! Daily field files, probe files and restart files.
module output_mod
  use kinds_mod, only: dp
  use input_mod, only: model_t, lin
  implicit none
  private
  public :: expand_name, expand_step, write_field, write_minutes, write_restart, read_restart, remove_restart, probe_header

contains

  ! (*(es<w>.<d>e3,:,"<sep>")) for the given number of significant digits
  function value_fmt(digits, sep) result(f)
    integer, intent(in) :: digits
    character(len=1), intent(in) :: sep
    character(len=:), allocatable :: f
    character(len=64) :: b
    write (b, '(a,i0,a,i0,a,a,a)') '(*(es', digits + 7, '.', digits - 1, 'e3,:,"', sep, '"))'
    f = trim(b)
  end function value_fmt

  ! replaces {period} by the period number (3 digits, zero padded)
  function expand_name(tmpl, period) result(r)
    character(len=*), intent(in) :: tmpl
    integer, intent(in) :: period
    character(len=:), allocatable :: r
    character(len=12) :: ps
    integer :: i
    if (period <= 999) then
      write (ps, '(i3.3)') period
    else
      write (ps, '(i0)') period
    end if
    i = index(tmpl, '{period}')
    if (i == 0) then
      r = trim(tmpl)
    else
      r = tmpl(1:i - 1) // trim(ps) // trim(tmpl(i + 8:))
    end if
  end function expand_name

  ! replaces {step} by the global step number (7 digits, zero padded)
  function expand_step(tmpl, step) result(r)
    character(len=*), intent(in) :: tmpl
    integer, intent(in) :: step
    character(len=:), allocatable :: r
    character(len=12) :: ss
    integer :: i
    if (step <= 9999999) then
      write (ss, '(i7.7)') step
    else
      write (ss, '(i0)') step
    end if
    i = index(tmpl, '{step}')
    if (i == 0) then
      r = trim(tmpl)
    else
      r = tmpl(1:i - 1) // trim(ss) // trim(tmpl(i + 6:))
    end if
  end function expand_step

  ! one block per layer (ILAY), one line per row (IROW), ICOL across (MODFLOW order)
  subroutine write_field(m, c, cm, period, step, path)
    type(model_t), intent(in) :: m
    real(dp), intent(in) :: c(:), cm
    integer, intent(in) :: period, step
    character(len=*), intent(in) :: path
    integer :: u, ios, ir, il, ic
    character(len=:), allocatable :: fmt
    fmt = value_fmt(m%field_digits, ',')
    open (newunit=u, file=path, status='replace', action='write', iostat=ios)
    if (ios /= 0) then
      write (*, '(a)') 'memdif3d: warning: cannot write ' // trim(path)
      return
    end if
    write (u, '(a,i0,a,i0,a,f0.3,a,es23.15e3)') '# memdif3d field, period ', period, ', step ', step, &
      ', minutes ', real(step, dp) * m%step_len, ', CM ', cm
    do il = 1, m%nlay
      write (u, '(a,i0)') '# ILAY ', il
      do ir = 1, m%nrow
        write (u, fmt) (c(lin(m, il, ir, ic)), ic=1, m%ncol)
      end do
    end do
    close (u)
  end subroutine write_field

  ! selected layers as a compact list, e.g. 1-5,9
  function layer_list(sel) result(r)
    logical, intent(in) :: sel(:)
    character(len=:), allocatable :: r
    character(len=32) :: b
    integer :: i, j
    r = ''
    i = 1
    do while (i <= size(sel))
      if (.not. sel(i)) then
        i = i + 1
        cycle
      end if
      j = i
      do while (j < size(sel))
        if (.not. sel(j + 1)) exit
        j = j + 1
      end do
      if (j > i) then
        write (b, '(i0,a,i0)') i, '-', j
      else
        write (b, '(i0)') i
      end if
      if (len(r) > 0) r = r // ','
      r = r // trim(b)
      i = j + 1
    end do
  end function layer_list

  ! one step of the minutes file. HORIZONTAL: a header, then one line per IROW with the selected layers side by
  ! side (ICOL fastest inside each layer). VERTICAL: a header and a tile of NROW lines per selected layer.
  subroutine write_minutes(m, c, u, step)
    type(model_t), intent(in) :: m
    real(dp), intent(in) :: c(:)
    integer, intent(in) :: u, step
    integer :: ir, il, ic, k, bw
    integer, allocatable :: lsel(:)
    character(len=:), allocatable :: lab
    character(len=16) :: ln
    character(len=:), allocatable :: fmt
    character(len=24) :: ts
    fmt = value_fmt(m%min_digits, ' ')
    lsel = pack([(il, il=1, m%nlay)], m%min_lay)
    write (ts, '(f0.3)') real(step, dp) * m%step_len
    if (ts(1:1) == '.') ts = '0' // ts
    if (m%min_horizontal) then
      write (u, '(a,i0,a,a,a,a,a,i0,a,i0)') '# STEP ', step, ' TIME ', trim(ts), ' LAYERS ', layer_list(m%min_lay), &
        ' NROW ', m%nrow, ' NCOL ', m%ncol
      ! label line: the layer number over the first value of each layer, '#' in the first position
      bw = m%ncol * (m%min_digits + 8)
      allocate (character(len=bw * size(lsel)) :: lab)
      lab(:) = ''
      do k = 1, size(lsel)
        write (ln, '(a,i0)') 'ILAY ', lsel(k)
        if (k == 1) ln = '#' // trim(ln)
        lab((k - 1) * bw + 1:(k - 1) * bw + len_trim(ln)) = trim(ln)
      end do
      write (u, '(a)') lab
      do ir = 1, m%nrow
        write (u, fmt) ((c(lin(m, lsel(k), ir, ic)), ic=1, m%ncol), k=1, size(lsel))
      end do
    else
      do il = 1, m%nlay
        if (.not. m%min_lay(il)) cycle
        write (u, '(a,i0,a,a,a,i0,a,i0,a,i0)') '# STEP ', step, ' TIME ', trim(ts), &
          ' ILAY ', il, ' NROW ', m%nrow, ' NCOL ', m%ncol
        do ir = 1, m%nrow
          write (u, fmt) (c(lin(m, il, ir, ic)), ic=1, m%ncol)
        end do
      end do
    end if
  end subroutine write_minutes

  subroutine probe_header(m, line)
    type(model_t), intent(in) :: m
    character(len=*), intent(out) :: line
    character(len=40) :: lab
    integer :: i
    line = 'step,time'
    do i = 1, m%nprobe
      if (m%probe_ijk(1, i) == 0) then
        lab = 'SOURCE'
      else
        write (lab, '(i0,a,i0,a,i0)') m%probe_ijk(1, i), '_', m%probe_ijk(2, i), '_', m%probe_ijk(3, i)
      end if
      line = trim(line) // ',' // trim(lab)
    end do
  end subroutine probe_header

  ! restart files alternate between <name>.1 and <name>.2 so a crash while writing keeps the previous one
  subroutine write_restart(m, c, cm, period, step, base)
    type(model_t), intent(in) :: m
    real(dp), intent(in) :: c(:), cm
    integer, intent(in) :: period, step
    character(len=*), intent(in) :: base
    character(len=:), allocatable :: path
    integer :: u, ios
    path = trim(base) // merge('.1', '.2', mod(period, 2) == 1)
    open (newunit=u, file=path, status='replace', action='write', iostat=ios)
    if (ios /= 0) then
      write (*, '(a)') 'memdif3d: warning: cannot write ' // path
      return
    end if
    write (u, '(a)') 'MEMDIF3D-RESTART 2'
    write (u, '(3(i0,1x))') m%nlay, m%nrow, m%ncol
    write (u, '(2(i0,1x))') period, step
    write (u, '(es26.17e3)') cm
    write (u, '(4es26.17e3)') c
    write (u, '(a)') 'END'
    close (u)
  end subroutine write_restart

  logical function try_read(m, path, c, cm, period, step)
    type(model_t), intent(in) :: m
    character(len=*), intent(in) :: path
    real(dp), intent(out) :: c(:), cm
    integer, intent(out) :: period, step
    character(len=64) :: line
    integer :: u, ios, nlay, nrow, ncol
    try_read = .false.
    open (newunit=u, file=path, status='old', action='read', iostat=ios)
    if (ios /= 0) return
    read (u, '(a)', iostat=ios) line
    if (ios /= 0 .or. trim(line) /= 'MEMDIF3D-RESTART 2') goto 90
    read (u, *, iostat=ios) nlay, nrow, ncol
    if (ios /= 0 .or. nlay /= m%nlay .or. nrow /= m%nrow .or. ncol /= m%ncol) goto 90
    read (u, *, iostat=ios) period, step
    if (ios /= 0) goto 90
    read (u, *, iostat=ios) cm
    if (ios /= 0) goto 90
    read (u, '(4es26.17e3)', iostat=ios) c
    if (ios /= 0) goto 90
    read (u, '(a)', iostat=ios) line
    if (ios /= 0 .or. trim(line) /= 'END') goto 90
    try_read = .true.
90  close (u)
  end function try_read

  ! newest valid restart file of the two slots
  logical function read_restart(m, base, c, cm, period, step)
    type(model_t), intent(in) :: m
    character(len=*), intent(in) :: base
    real(dp), intent(out) :: c(:), cm
    integer, intent(out) :: period, step
    real(dp), allocatable :: c2(:)
    real(dp) :: cm2
    integer :: p2, s2
    logical :: ok1, ok2
    allocate (c2(size(c)))
    ok1 = try_read(m, trim(base) // '.1', c, cm, period, step)
    ok2 = try_read(m, trim(base) // '.2', c2, cm2, p2, s2)
    if (ok2 .and. (.not. ok1 .or. p2 > period)) then
      c = c2
      cm = cm2
      period = p2
      step = s2
    end if
    read_restart = ok1 .or. ok2
  end function read_restart

  subroutine remove_restart(base)
    character(len=*), intent(in) :: base
    integer :: u, ios, k
    do k = 1, 2
      open (newunit=u, file=trim(base) // merge('.1', '.2', k == 1), status='old', iostat=ios)
      if (ios == 0) close (u, status='delete')
    end do
  end subroutine remove_restart

end module output_mod
