! Reads the memdif3d text packages (see docs/INPUT_SPEC.md) and builds the work lists
! used by the solver.
module input_mod
  use kinds_mod, only: dp
  implicit none
  private
  public :: model_t, read_model, lin, fatal

  type :: str_t
    character(len=:), allocatable :: s
  end type str_t

  type :: model_t
    character(len=256) :: title = ''
    integer :: nrow = 0, ncol = 0, nlay = 0, ntot = 0
    ! time
    real(dp) :: step_len = 1.0_dp
    integer :: steps_per_period = 0, nperiods = 0
    ! coefficients
    real(dp) :: ks = 0.0_dp, km = 0.0_dp      ! per step, divided by the retardation
    real(dp) :: kmem = 0.0_dp                 ! membrane coefficient used by the source cell
    real(dp) :: ksand = 0.0_dp                ! sand coefficient (no R) used by the source cell at a hole
    real(dp) :: vol = 0.0_dp, cm0 = 0.0_dp, vel = 0.0_dp
    ! state at the start
    real(dp), allocatable :: c0(:)
    ! fluid cells: linear index, six neighbours (>0 cell, 0 none, <0 source), advection neighbour
    integer :: nf = 0
    integer, allocatable :: fcell(:), nb(:, :), advnb(:)
    ! ghost cells, in evaluation order: value = gfac * cell(gsrc), or gfac if gsrc = 0
    integer :: ng = 0
    integer, allocatable :: gcell(:), gsrc(:)
    real(dp), allocatable :: gfac(:)
    ! source faces (linear index of the ILAY = 1 cell under each face)
    ! fkind: 1 membrane, 2 hole (open, sand coefficient); closed faces are not listed
    integer :: nfaces = 0, nholes = 0, nclosed = 0
    integer, allocatable :: face(:), fkind(:)
    ! probes: ijk(:, n) = 0 0 0 means the source cell
    integer :: nprobe = 0
    integer, allocatable :: probe_ijk(:, :)                ! (row, col, lay); 0 0 0 = source
    ! output control
    logical :: has_field = .false., has_probes = .false., has_restart = .false., has_snap = .false.
    character(len=256) :: field_out = '', probes_out = '', restart_out = '', snap_out = ''
    integer :: snap_every = 0
  end type model_t

  integer, parameter :: DXYZ(3, 6) = reshape([ 1, 0, 0,  -1, 0, 0,  0, 1, 0,  0, -1, 0,  0, 0, 1,  0, 0, -1], [3, 6])

contains

  subroutine fatal(msg)
    character(len=*), intent(in) :: msg
    write (*, '(a)') 'memdif3d: error: ' // trim(msg)
    error stop 1
  end subroutine fatal

  pure integer function lin(m, ir, ic, il)
    type(model_t), intent(in) :: m
    integer, intent(in) :: ir, ic, il
    lin = ic + m%ncol * ((ir - 1) + m%nrow * (il - 1))
  end function lin

  ! ---- small string helpers -------------------------------------------------------------
  function lower(s) result(r)
    character(len=*), intent(in) :: s
    character(len=len(s)) :: r
    integer :: i, c
    r = s
    do i = 1, len(s)
      c = iachar(s(i:i))
      if (c >= 65 .and. c <= 90) r(i:i) = achar(c + 32)
    end do
  end function lower

  integer function nwords(s)
    character(len=*), intent(in) :: s
    integer :: i
    logical :: inw
    nwords = 0
    inw = .false.
    do i = 1, len(s)
      if (s(i:i) == ' ') then
        inw = .false.
      else if (.not. inw) then
        inw = .true.
        nwords = nwords + 1
      end if
    end do
  end function nwords

  real(dp) function to_real(s, ios)
    character(len=*), intent(in) :: s
    integer, intent(out) :: ios
    to_real = 0.0_dp
    read (s, *, iostat=ios) to_real
  end function to_real

  integer function to_int(s, ios)
    character(len=*), intent(in) :: s
    integer, intent(out) :: ios
    to_int = 0
    read (s, *, iostat=ios) to_int
  end function to_int

  function word(s, k) result(w)
    character(len=*), intent(in) :: s
    integer, intent(in) :: k
    character(len=:), allocatable :: w
    integer :: i, n, st
    logical :: inw, sp
    n = 0
    st = 0
    inw = .false.
    w = ''
    do i = 1, len(s) + 1
      sp = .true.
      if (i <= len(s)) sp = (s(i:i) == ' ')
      if (sp) then
        if (inw) then
          inw = .false.
          if (n == k) then
            w = s(st:i - 1)
            return
          end if
        end if
      else if (.not. inw) then
        inw = .true.
        n = n + 1
        st = i
      end if
    end do
  end function word

  ! ---- file and block reading -------------------------------------------------------------
  subroutine read_lines(path, lines, n)
    character(len=*), intent(in) :: path
    type(str_t), allocatable, intent(out) :: lines(:)
    integer, intent(out) :: n
    type(str_t), allocatable :: tmp(:)
    character(len=8192) :: buf
    integer :: u, ios, cap, p, i
    open (newunit=u, file=path, status='old', action='read', iostat=ios)
    if (ios /= 0) call fatal('cannot open ' // trim(path))
    cap = 1024
    allocate (lines(cap))
    n = 0
    do
      read (u, '(a)', iostat=ios) buf
      if (ios /= 0) exit
      p = index(buf, '#')
      if (p > 0) buf(p:) = ' '
      do i = 1, len(buf)
        if (buf(i:i) == achar(9) .or. buf(i:i) == achar(13)) buf(i:i) = ' '
      end do
      if (len_trim(buf) == 0) cycle
      n = n + 1
      if (n > cap) then
        allocate (tmp(2 * cap))
        do i = 1, cap
          call move_alloc(lines(i)%s, tmp(i)%s)
        end do
        call move_alloc(tmp, lines)
        cap = 2 * cap
      end if
      lines(n)%s = trim(adjustl(buf))
    end do
    close (u)
  end subroutine read_lines

  subroutine find_block(lines, n, name, i0, i1, found)
    type(str_t), intent(in) :: lines(:)
    integer, intent(in) :: n
    character(len=*), intent(in) :: name
    integer, intent(out) :: i0, i1
    logical, intent(out) :: found
    integer :: i, j
    found = .false.
    i0 = 1
    i1 = 0
    do i = 1, n
      if (lower(word(lines(i)%s, 1)) == 'begin' .and. lower(word(lines(i)%s, 2)) == name) then
        do j = i + 1, n
          if (lower(word(lines(j)%s, 1)) == 'end') then
            i0 = i + 1
            i1 = j - 1
            found = .true.
            return
          end if
        end do
        call fatal('block ' // name // ' has no END')
      end if
    end do
  end subroutine find_block

  subroutine need_block(lines, n, name, file, i0, i1)
    type(str_t), intent(in) :: lines(:)
    integer, intent(in) :: n
    character(len=*), intent(in) :: name, file
    integer, intent(out) :: i0, i1
    logical :: found
    call find_block(lines, n, name, i0, i1, found)
    if (.not. found) call fatal('block ' // name // ' not found in ' // trim(file))
  end subroutine need_block

  function get_word(lines, i0, i1, key, file) result(w)
    type(str_t), intent(in) :: lines(:)
    integer, intent(in) :: i0, i1
    character(len=*), intent(in) :: key, file
    character(len=:), allocatable :: w
    integer :: i
    do i = i0, i1
      if (lower(word(lines(i)%s, 1)) == key) then
        w = word(lines(i)%s, 2)
        return
      end if
    end do
    call fatal('keyword ' // key // ' missing in ' // trim(file))
  end function get_word

  real(dp) function get_real(lines, i0, i1, key, file)
    type(str_t), intent(in) :: lines(:)
    integer, intent(in) :: i0, i1
    character(len=*), intent(in) :: key, file
    character(len=:), allocatable :: w
    integer :: ios
    w = get_word(lines, i0, i1, key, file)
    read (w, *, iostat=ios) get_real
    if (ios /= 0) call fatal('bad number for ' // key // ' in ' // trim(file))
  end function get_real

  integer function get_int(lines, i0, i1, key, file)
    type(str_t), intent(in) :: lines(:)
    integer, intent(in) :: i0, i1
    character(len=*), intent(in) :: key, file
    character(len=:), allocatable :: w
    integer :: ios
    w = get_word(lines, i0, i1, key, file)
    read (w, *, iostat=ios) get_int
    if (ios /= 0) call fatal('bad integer for ' // key // ' in ' // trim(file))
  end function get_int

  ! array: "KEY" line, then "INTERNAL" and free-format numbers, or "CONSTANT value"
  subroutine read_array(lines, i0, i1, key, file, arr)
    type(str_t), intent(in) :: lines(:)
    integer, intent(in) :: i0, i1
    character(len=*), intent(in) :: key, file
    real(dp), intent(out) :: arr(:)
    integer :: i, st, k, nt, ios
    character(len=:), allocatable :: w1
    st = 0
    do i = i0, i1
      if (lower(word(lines(i)%s, 1)) == key) then
        st = i
        exit
      end if
    end do
    if (st == 0) call fatal('array ' // key // ' missing in ' // trim(file))
    k = 0
    do i = st + 1, i1
      w1 = lower(word(lines(i)%s, 1))
      if (w1 == 'internal') cycle
      if (w1 == 'constant') then
        arr(1) = to_real(word(lines(i)%s, 2), ios)
        if (ios /= 0) call fatal('bad CONSTANT for ' // key)
        arr(:) = arr(1)
        k = size(arr)
        exit
      end if
      nt = nwords(lines(i)%s)
      if (k + nt > size(arr)) call fatal('too many values for ' // key // ' in ' // trim(file))
      read (lines(i)%s, *, iostat=ios) arr(k + 1:k + nt)
      if (ios /= 0) call fatal('cannot read values of ' // key // ' in ' // trim(file))
      k = k + nt
      if (k == size(arr)) exit
    end do
    if (k /= size(arr)) call fatal('array ' // key // ' has too few values in ' // trim(file))
  end subroutine read_array

  integer function dir_index(s, file)
    character(len=*), intent(in) :: s, file
    select case (lower(s))
    case ('+row'); dir_index = 1
    case ('-row'); dir_index = 2
    case ('+col'); dir_index = 3
    case ('-col'); dir_index = 4
    case ('+lay'); dir_index = 5
    case ('-lay'); dir_index = 6
    case default
      dir_index = 0
      call fatal('bad direction ' // trim(s) // ' in ' // trim(file))
    end select
  end function dir_index

  function pkg_path(nam, nn, key, dir, required) result(p)
    type(str_t), intent(in) :: nam(:)
    integer, intent(in) :: nn
    character(len=*), intent(in) :: key, dir
    logical, intent(in) :: required
    character(len=:), allocatable :: p
    integer :: i0, i1, i
    call need_block(nam, nn, 'packages', 'name file', i0, i1)
    p = ''
    do i = i0, i1
      if (lower(word(nam(i)%s, 1)) == key) then
        p = trim(dir) // word(nam(i)%s, 2)
        return
      end if
    end do
    if (required) call fatal('package ' // key // ' not listed in the name file')
  end function pkg_path

  ! ---- the model ------------------------------------------------------------------------------
  subroutine read_model(namefile, m)
    character(len=*), intent(in) :: namefile
    type(model_t), intent(out) :: m
    type(str_t), allocatable :: nam(:), t(:)
    character(len=:), allocatable :: dir, f
    character(len=:), allocatable :: w
    real(dp), allocatable :: buf(:), advmask(:)
    integer, allocatable :: idom(:), kmap(:)
    integer, allocatable :: isface(:, :)           ! 0 none, 1 membrane, 2 hole, 3 closed
    integer :: nn, nt, i0, i1, i, k, p, d, ir, ic, il, jr, jc, jl, ios, tr, tc, tl, ip
    real(dp) :: dsand(4), dmem(4), por, rho, kd, rr, ksand, kmem
    logical :: found

    i = scan(namefile, '/\', back=.true.)
    dir = ''
    if (i > 0) dir = namefile(1:i)
    call read_lines(namefile, nam, nn)
    call find_block(nam, nn, 'options', i0, i1, found)
    if (found) then
      do i = i0, i1
        if (lower(word(nam(i)%s, 1)) == 'title') m%title = adjustl(nam(i)%s(6:))
      end do
    end if

    ! TDIS
    f = pkg_path(nam, nn, 'tdis', dir, .true.)
    call read_lines(f, t, nt)
    call need_block(t, nt, 'timing', f, i0, i1)
    m%step_len = get_real(t, i0, i1, 'step_length', f)
    m%steps_per_period = get_int(t, i0, i1, 'steps_per_period', f)
    m%nperiods = get_int(t, i0, i1, 'nperiods', f)

    ! DIS
    f = pkg_path(nam, nn, 'dis', dir, .true.)
    call read_lines(f, t, nt)
    call need_block(t, nt, 'dimensions', f, i0, i1)
    m%nrow = get_int(t, i0, i1, 'nrow', f)
    m%ncol = get_int(t, i0, i1, 'ncol', f)
    m%nlay = get_int(t, i0, i1, 'nlay', f)
    m%ntot = m%nrow * m%ncol * m%nlay
    allocate (buf(m%ntot), idom(m%ntot), advmask(m%ntot))
    call need_block(t, nt, 'griddata', f, i0, i1)
    call read_array(t, i0, i1, 'idomain', f, buf)
    idom = nint(buf)
    if (any(idom < 0 .or. idom > 2)) call fatal('IDOMAIN must contain 0, 1 or 2')

    ! IC
    f = pkg_path(nam, nn, 'ic', dir, .true.)
    call read_lines(f, t, nt)
    call need_block(t, nt, 'griddata', f, i0, i1)
    allocate (m%c0(m%ntot))
    call read_array(t, i0, i1, 'strt', f, m%c0)

    ! DSP
    f = pkg_path(nam, nn, 'dsp', dir, .true.)
    call read_lines(f, t, nt)
    call need_block(t, nt, 'sand', f, i0, i1)
    dsand = [get_real(t, i0, i1, 'diffusion', f), get_real(t, i0, i1, 'tortuosity', f), &
             get_real(t, i0, i1, 'porosity', f), get_real(t, i0, i1, 'length', f)]
    call need_block(t, nt, 'membrane', f, i0, i1)
    dmem = [get_real(t, i0, i1, 'diffusion', f), get_real(t, i0, i1, 'tortuosity', f), &
            get_real(t, i0, i1, 'porosity', f), get_real(t, i0, i1, 'length', f)]
    ksand = dsand(1) * dsand(3) / dsand(4) / dsand(2)      ! D * porosity / length / tortuosity
    kmem = dmem(1) * dmem(3) / dmem(4) / dmem(2)

    ! MST
    f = pkg_path(nam, nn, 'mst', dir, .true.)
    call read_lines(f, t, nt)
    call need_block(t, nt, 'options', f, i0, i1)
    por = get_real(t, i0, i1, 'porosity', f)
    rho = get_real(t, i0, i1, 'bulk_density', f)
    kd = get_real(t, i0, i1, 'kd', f)
    rr = por + rho * kd
    m%ks = ksand / rr
    m%km = kmem / rr
    m%kmem = kmem
    m%ksand = ksand

    ! SRC
    f = pkg_path(nam, nn, 'src', dir, .true.)
    call read_lines(f, t, nt)
    call need_block(t, nt, 'source', f, i0, i1)
    m%vol = get_real(t, i0, i1, 'volume', f)
    m%cm0 = get_real(t, i0, i1, 'start_conc', f)
    call need_block(t, nt, 'faces', f, i0, i1)
    allocate (m%face(i1 - i0 + 1), m%fkind(i1 - i0 + 1), isface(m%nrow, m%ncol))
    isface = 0
    m%nfaces = 0
    do i = i0, i1
      read (t(i)%s, *, iostat=ios) ir, ic
      if (ios /= 0) call fatal('bad face line in ' // trim(f))
      if (ir < 1 .or. ir > m%nrow .or. ic < 1 .or. ic > m%ncol) call fatal('face outside the grid in ' // trim(f))
      if (isface(ir, ic) /= 0) call fatal('face listed twice in ' // trim(f))
      w = lower(word(t(i)%s, 3))
      select case (w)
      case ('', 'membrane')
        isface(ir, ic) = 1
      case ('hole')
        isface(ir, ic) = 2
        m%nholes = m%nholes + 1
      case ('closed')
        isface(ir, ic) = 3
        m%nclosed = m%nclosed + 1
      case default
        call fatal('face type must be MEMBRANE, HOLE or CLOSED in ' // trim(f))
      end select
      if (isface(ir, ic) /= 3) then
        m%nfaces = m%nfaces + 1
        m%face(m%nfaces) = lin(m, ir, ic, 1)
        m%fkind(m%nfaces) = isface(ir, ic)
      end if
    end do

    ! ADV
    f = pkg_path(nam, nn, 'adv', dir, .true.)
    call read_lines(f, t, nt)
    call need_block(t, nt, 'options', f, i0, i1)
    m%vel = get_real(t, i0, i1, 'velocity', f)
    call need_block(t, nt, 'griddata', f, i0, i1)
    call read_array(t, i0, i1, 'advmask', f, advmask)

    ! fluid cells and default neighbours
    m%nf = count(idom == 1)
    allocate (m%fcell(m%nf), m%nb(6, m%nf), m%advnb(m%nf), kmap(m%ntot))
    kmap = 0
    k = 0
    do ic = 1, m%ncol
      do ir = 1, m%nrow
        do il = 1, m%nlay
          p = lin(m, ir, ic, il)
          if (idom(p) /= 1) cycle
          k = k + 1
          m%fcell(k) = p
          kmap(p) = k
          do d = 1, 6
            m%nb(d, k) = 0
            if (d == 6 .and. il == 1 .and. isface(ir, ic) > 0) then
              if (isface(ir, ic) == 1) m%nb(d, k) = -1
              if (isface(ir, ic) == 2) m%nb(d, k) = -2
              cycle                                   ! closed face: no neighbour
            end if
            jr = ir + DXYZ(1, d)
            jc = ic + DXYZ(2, d)
            jl = il + DXYZ(3, d)
            if (jr < 1 .or. jr > m%nrow .or. jc < 1 .or. jc > m%ncol .or. jl < 1 .or. jl > m%nlay) cycle
            if (idom(lin(m, jr, jc, jl)) /= 0) m%nb(d, k) = lin(m, jr, jc, jl)
          end do
          m%advnb(k) = 0
          if (advmask(p) > 0.5_dp .and. ir < m%nrow) m%advnb(k) = lin(m, ir + 1, ic, il)
        end do
      end do
    end do

    ! BND
    f = pkg_path(nam, nn, 'bnd', dir, .true.)
    call read_lines(f, t, nt)
    call need_block(t, nt, 'ghosts', f, i0, i1)
    m%ng = i1 - i0 + 1
    allocate (m%gcell(m%ng), m%gsrc(m%ng), m%gfac(m%ng))
    do i = i0, i1
      w = lower(word(t(i)%s, 4))
      read (t(i)%s, *, iostat=ios) il, ir, ic
      if (ios /= 0) call fatal('bad ghost line in ' // trim(f))
      ip = i - i0 + 1
      m%gcell(ip) = lin(m, ir, ic, il)
      if (w == 'fixed') then
        m%gsrc(ip) = 0
        m%gfac(ip) = to_real(word(t(i)%s, 5), ios)
      else if (w == 'copy') then
        tl = to_int(word(t(i)%s, 5), ios)
        tr = to_int(word(t(i)%s, 6), ios)
        tc = to_int(word(t(i)%s, 7), ios)
        m%gsrc(ip) = lin(m, tr, tc, tl)
        m%gfac(ip) = to_real(word(t(i)%s, 8), ios)
      else
        call fatal('ghost type must be COPY or FIXED in ' // trim(f))
      end if
      if (ios /= 0) call fatal('bad ghost line in ' // trim(f))
    end do
    if (count(idom == 2) /= m%ng) call fatal('number of ghost lines differs from the number of IDOMAIN = 2 cells')

    call need_block(t, nt, 'neighbor_overrides', f, i0, i1)
    do i = i0, i1
      read (t(i)%s, *, iostat=ios) il, ir, ic
      if (ios /= 0) call fatal('bad override line in ' // trim(f))
      d = dir_index(word(t(i)%s, 4), f)
      k = kmap(lin(m, ir, ic, il))
      if (k == 0) call fatal('neighbor override on a cell that is not a fluid cell')
      w = lower(word(t(i)%s, 5))
      select case (w)
      case ('omit')
        m%nb(d, k) = 0
      case ('source')
        m%nb(d, k) = -1
      case ('set')
        tl = to_int(word(t(i)%s, 6), ios)
        tr = to_int(word(t(i)%s, 7), ios)
        tc = to_int(word(t(i)%s, 8), ios)
        if (ios /= 0) call fatal('bad override line in ' // trim(f))
        if (tr < 1 .or. tr > m%nrow .or. tc < 1 .or. tc > m%ncol .or. tl < 1 .or. tl > m%nlay) &
          call fatal('override target outside the grid')
        m%nb(d, k) = lin(m, tr, tc, tl)
      case default
        call fatal('override kind must be OMIT, SOURCE or SET')
      end select
    end do

    ! OC
    f = pkg_path(nam, nn, 'oc', dir, .false.)
    if (len(f) > 0) then
      call read_lines(f, t, nt)
      call find_block(t, nt, 'options', i0, i1, found)
      if (found) then
        do i = i0, i1
          w = lower(word(t(i)%s, 1))
          if (lower(word(t(i)%s, 2)) /= 'fileout') cycle
          select case (w)
          case ('daily_field')
            m%has_field = .true.
            m%field_out = word(t(i)%s, 3)
          case ('probes')
            m%has_probes = .true.
            m%probes_out = word(t(i)%s, 3)
          case ('restart')
            m%has_restart = .true.
            m%restart_out = word(t(i)%s, 3)
          case ('snapshot')
            m%has_snap = .true.
            m%snap_out = word(t(i)%s, 3)
            if (lower(word(t(i)%s, 4)) /= 'every') call fatal('SNAPSHOT needs: SNAPSHOT FILEOUT name EVERY n')
            m%snap_every = to_int(word(t(i)%s, 5), ios)
            if (ios /= 0 .or. m%snap_every < 1) call fatal('SNAPSHOT EVERY needs a positive integer')
          end select
        end do
      end if
      call find_block(t, nt, 'probes', i0, i1, found)
      if (found) then
        m%nprobe = i1 - i0 + 1
        allocate (m%probe_ijk(3, m%nprobe))
        do i = i0, i1
          ip = i - i0 + 1
          if (lower(word(t(i)%s, 1)) == 'source') then
            m%probe_ijk(:, ip) = 0
          else
            read (t(i)%s, *, iostat=ios) il, ir, ic
            if (ios /= 0) call fatal('bad probe line in ' // trim(f))
            if (ir < 1 .or. ir > m%nrow .or. ic < 1 .or. ic > m%ncol .or. il < 1 .or. il > m%nlay) &
              call fatal('probe outside the grid')
            m%probe_ijk(:, ip) = [ir, ic, il]
          end if
        end do
      end if
    end if
  end subroutine read_model

end module input_mod
