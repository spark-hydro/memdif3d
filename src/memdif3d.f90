! memdif3d: membrane diffusion from a fully mixed source cell into a 3D porous medium.
! Model: docs/MODEL_SPEC.md   Input: docs/INPUT_SPEC.md
program memdif3d
  use kinds_mod, only: dp
  use version_mod, only: VERSION
  use banner_mod, only: print_banner, run_stamp
  use input_mod, only: model_t, read_model, lin, fatal
  use solver_mod, only: advance, stability
  use output_mod, only: expand_name, expand_step, write_field, write_restart, read_restart, remove_restart, probe_header
  implicit none

  type(model_t) :: m
  character(len=512) :: namefile, arg
  character(len=1024) :: line
  real(dp), allocatable :: buf(:, :)
  real(dp) :: cm, cmn, tsec
  integer :: nargs, i, ip, is, cur, ip0, gstep, step0, pu, ios, c0, c1, rate, ovr_np, ovr_spp, ovr_snap
  logical :: fresh, per_period, pok, force
  real(dp) :: smax, ssrc
  integer :: worst, wl, wr, wc
  character(len=:), allocatable :: pfile

  nargs = command_argument_count()
  if (nargs == 0) then
    call print_usage()
    stop
  end if

  call get_command_argument(1, arg)
  select case (trim(arg))
  case ('--version', '-v')
    call print_banner()
    stop
  case ('--help', '-h')
    call print_usage()
    stop
  end select

  namefile = arg
  fresh = .false.
  force = .false.
  ovr_np = -1
  ovr_spp = -1
  ovr_snap = -1
  i = 2
  do while (i <= nargs)
    call get_command_argument(i, arg)
    select case (trim(arg))
    case ('--fresh')
      fresh = .true.
    case ('--force')
      force = .true.
    case ('--nperiods')
      i = i + 1
      call get_command_argument(i, arg)
      read (arg, *, iostat=ios) ovr_np
      if (ios /= 0) call fatal('--nperiods needs an integer')
    case ('--snapshot-every')
      i = i + 1
      call get_command_argument(i, arg)
      read (arg, *, iostat=ios) ovr_snap
      if (ios /= 0 .or. ovr_snap < 1) call fatal('--snapshot-every needs a positive integer')
    case ('--steps-per-period')
      i = i + 1
      call get_command_argument(i, arg)
      read (arg, *, iostat=ios) ovr_spp
      if (ios /= 0) call fatal('--steps-per-period needs an integer')
    case default
      call fatal('unknown option ' // trim(arg))
    end select
    i = i + 1
  end do

  call read_model(trim(namefile), m)
  if (ovr_np > 0) m%nperiods = ovr_np
  if (ovr_spp > 0) m%steps_per_period = ovr_spp
  if (ovr_snap > 0) then
    m%snap_every = ovr_snap
    if (.not. m%has_snap) m%snap_out = 'snap_{step}.csv'
    m%has_snap = .true.
  end if

  call print_banner()
  print '(a)', ' Run started ' // run_stamp()
  print '(a)', ' Reading ' // trim(namefile) // ' . . .'
  if (len_trim(m%title) > 0) print '(a)', ' case: ' // trim(m%title)
  print '(a,3(i0,1x),a,i0,a,i0,a,i0,a)', 'grid (lay row col): ', m%nlay, m%nrow, m%ncol, ' | fluid ', m%nf, ' ghost ', m%ng, &
    ' source faces ', m%nfaces, ''
  if (m%nholes > 0 .or. m%nclosed > 0) print '(a,i0,a,i0,a,i0)', 'faces: membrane ', m%nfaces - m%nholes, &
    ' | hole ', m%nholes, ' | closed ', m%nclosed
  print '(a,es10.3,a,es10.3,a,es10.3)', 'ks/R = ', m%ks, '  km/R = ', m%km, '  velocity = ', m%vel
  print '(a,i0,a,i0,a)', 'run: ', m%nperiods, ' periods x ', m%steps_per_period, ' steps'

  ! explicit scheme: refuse to run when it would be unstable
  call stability(m, smax, worst, ssrc)
  if (worst > 0) then
    wc = mod(worst - 1, m%ncol) + 1
    wr = mod((worst - 1) / m%ncol, m%nrow) + 1
    wl = (worst - 1) / (m%ncol * m%nrow) + 1
    print '(a,f6.3,a,3(i0,1x),a)', 'stability: largest coefficient sum = ', smax, ' at cell (lay row col) ', wl, wr, wc, '(limit 1)'
  end if
  print '(a,es10.3,a)', 'stability: source cell sum         = ', ssrc, ' (limit 1)'
  if (m%vel < 0.0_dp .and. any(m%advnb > 0)) &
    call fatal('VELOCITY must not be negative (upwind term runs towards lower IROW only)')
  if (smax > 1.0_dp .or. ssrc > 1.0_dp) then
    if (force) then
      print '(a)', 'warning: the explicit scheme is unstable for these coefficients; running anyway (--force)'
    else
      call fatal('explicit scheme unstable: coefficient sum above 1. Lower DIFFUSION, raise POROSITY/KD (retardation), ' &
                 // 'reduce VELOCITY or the step, or use --force')
    end if
  end if

  allocate (buf(m%ntot, 2))
  buf(:, 1) = m%c0
  buf(:, 2) = m%c0                     ! solid cells never change, so both buffers can start equal
  cur = 1
  cm = m%cm0
  ip0 = 1
  step0 = 0

  if (m%has_restart) then
    if (fresh) then
      call remove_restart(m%restart_out)
    else if (read_restart(m, m%restart_out, buf(:, 1), cm, ip, step0)) then
      buf(:, 2) = buf(:, 1)
      ip0 = ip + 1
      print '(a,i0,a,i0,a)', 'restart: continuing after period ', ip, ' (step ', step0, ')'
    end if
  end if
  if (ip0 > m%nperiods) then
    print '(a)', 'nothing to do: all periods are already finished'
    stop
  end if

  per_period = .false.
  if (m%has_probes .and. m%nprobe > 0) per_period = index(m%probes_out, '{period}') > 0
  call system_clock(c0, rate)

  do ip = ip0, m%nperiods
    pok = .false.
    if (m%has_probes .and. m%nprobe > 0) then
      pfile = expand_name(m%probes_out, ip)
      if (per_period .or. ip == ip0 .and. step0 == 0) then
        open (newunit=pu, file=pfile, status='replace', action='write', iostat=ios)
        if (ios == 0) then
          call probe_header(m, line)
          write (pu, '(a)') trim(line)
        end if
      else
        open (newunit=pu, file=pfile, status='old', position='append', action='write', iostat=ios)
      end if
      pok = (ios == 0)
      if (.not. pok) print '(a)', 'warning: cannot open ' // pfile
    end if

    do is = 1, m%steps_per_period
      call advance(m, buf(:, cur), cm, buf(:, 3 - cur), cmn)
      cm = cmn
      cur = 3 - cur
      gstep = (ip - 1) * m%steps_per_period + is
      if (m%has_snap) then
        if (mod(gstep, m%snap_every) == 0) &
          call write_field(m, buf(:, cur), cm, ip, gstep, expand_step(m%snap_out, gstep))
      end if
      if (pok) then
        write (pu, '(i0,",",f0.3,*(:,",",es23.15e3))') gstep, real(gstep, dp) * m%step_len, &
          (probe_value(m, buf(:, cur), cm, i), i=1, m%nprobe)
      end if
    end do
    if (pok) close (pu)

    gstep = ip * m%steps_per_period
    if (m%has_field) call write_field(m, buf(:, cur), cm, ip, gstep, expand_name(m%field_out, ip))
    if (m%has_restart) call write_restart(m, buf(:, cur), cm, ip, gstep, m%restart_out)

    call system_clock(c1)
    tsec = real(c1 - c0, dp) / real(rate, dp)
    print '(a,i0,a,i0,a,f0.1,a,f10.7,a,f7.1,a)', 'period ', ip, '/', m%nperiods, '  t = ', &
      real(gstep, dp) * m%step_len, ' min  CM = ', cm, '   elapsed ', tsec, ' s'
  end do

  print '(a)', ''
  print '(a)', ' Run finished ' // run_stamp()
  print '(a,f7.1,a)', ' Normal termination, ', tsec, ' s'

contains

  real(dp) function probe_value(mm, c, csrc, k)
    type(model_t), intent(in) :: mm
    real(dp), intent(in) :: c(:), csrc
    integer, intent(in) :: k
    if (mm%probe_ijk(1, k) == 0) then
      probe_value = csrc
    else
      probe_value = c(lin(mm, mm%probe_ijk(1, k), mm%probe_ijk(2, k), mm%probe_ijk(3, k)))
    end if
  end function probe_value

  subroutine print_usage()
    print '(a)', 'memdif3d ' // VERSION
    print '(a)', 'Usage: memdif3d <namefile> [--fresh] [--force] [--nperiods N] [--steps-per-period N] [--snapshot-every N]'
    print '(a)', '       memdif3d --version | --help'
    print '(a)', '  --fresh              ignore and delete restart files, start from the initial state'
    print '(a)', '  --force              run even if the stability check fails'
    print '(a)', '  --snapshot-every N   also write the field every N steps (snap_{step}.csv)'
    print '(a)', '  --nperiods N         override NPERIODS of the TDIS package'
    print '(a)', '  --steps-per-period N override STEPS_PER_PERIOD'
  end subroutine print_usage

end program memdif3d
