! Daily field files, probe files and restart files.
module output_mod
  use kinds_mod, only: dp
  use input_mod, only: model_t, lin
  implicit none
  private
  public :: expand_name, write_field, write_restart, read_restart, remove_restart, probe_header

contains

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

  ! one block per slice (IY), one line per row (IX), IZ across: the same tiles as the spreadsheet
  subroutine write_field(m, c, cm, period, step, path)
    type(model_t), intent(in) :: m
    real(dp), intent(in) :: c(:), cm
    integer, intent(in) :: period, step
    character(len=*), intent(in) :: path
    integer :: u, ios, ix, iy, iz
    open (newunit=u, file=path, status='replace', action='write', iostat=ios)
    if (ios /= 0) then
      write (*, '(a)') 'memdif3d: warning: cannot write ' // trim(path)
      return
    end if
    write (u, '(a,i0,a,i0,a,f0.3,a,es23.15e3)') '# memdif3d field, period ', period, ', step ', step, &
      ', minutes ', real(step, dp) * m%step_len, ', CM ', cm
    do iy = 1, m%ny
      write (u, '(a,i0)') '# IY ', iy
      do ix = 1, m%nx
        write (u, '(*(es23.15e3,:,","))') (c(lin(m, ix, iy, iz)), iz=1, m%nz)
      end do
    end do
    close (u)
  end subroutine write_field

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
    write (u, '(a)') 'MEMDIF3D-RESTART 1'
    write (u, '(3(i0,1x))') m%nx, m%ny, m%nz
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
    integer :: u, ios, nx, ny, nz
    try_read = .false.
    open (newunit=u, file=path, status='old', action='read', iostat=ios)
    if (ios /= 0) return
    read (u, '(a)', iostat=ios) line
    if (ios /= 0 .or. line(1:16) /= 'MEMDIF3D-RESTART') goto 90
    read (u, *, iostat=ios) nx, ny, nz
    if (ios /= 0 .or. nx /= m%nx .or. ny /= m%ny .or. nz /= m%nz) goto 90
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
