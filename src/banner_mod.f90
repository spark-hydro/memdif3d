! Start-up banner, in the style of the SWAT-MODFLOW3 banner.
module banner_mod
  use version_mod
  implicit none
  private
  public :: print_banner, run_stamp

contains

  subroutine print_banner()
    print '(a)', ''
    print '(a)', '               memdif3d ' // VERSION
    print '(a)', '      Membrane diffusion in 3D: a fully mixed source cell'
    print '(a)', '      leaking through a membrane into a porous medium'
    print '(a)', ''
    if (len_trim(GIT_TAG) > 0 .and. GIT_TAG /= VERSION) print '(a)', '      source   ' // trim(GIT_TAG)
    print '(a)', '      compiler ' // trim(COMPILER) // ', ' // trim(BUILD_TYPE) // ', ' // trim(HOST_SYSTEM)
    print '(a)', '      built    ' // trim(BUILT)
    print '(a)', ''
    if (len_trim(AUTHOR) > 0) print '(a)', '      Developed by ' // trim(AUTHOR)
    if (len_trim(DEPARTMENT) > 0) print '(a)', '      ' // trim(DEPARTMENT)
    if (len_trim(INSTITUTION) > 0) print '(a)', '      ' // trim(INSTITUTION)
    if (len_trim(CONTACT) > 0) print '(a)', '      ' // trim(CONTACT)
    print '(a)', '      MIT License'
    print '(a)', ''
  end subroutine print_banner

  ! "2026-10-22 15:30:12"
  function run_stamp() result(s)
    character(len=19) :: s
    integer :: v(8)
    call date_and_time(values=v)
    write (s, '(i4.4,"-",i2.2,"-",i2.2," ",i2.2,":",i2.2,":",i2.2)') v(1), v(2), v(3), v(5), v(6), v(7)
  end function run_stamp

end module banner_mod
