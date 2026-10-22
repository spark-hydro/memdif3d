! MEMDIF3D: membrane diffusion from a fully mixed source cell into a 3D porous medium.
! Skeleton: command line handling only. The model itself follows docs/MODEL_SPEC.md.
program memdif3d
  use version_mod, only: VERSION, BUILD_TYPE
  implicit none
  character(len=256) :: arg

  if (command_argument_count() == 0) then
    call print_usage()
    stop
  end if

  call get_command_argument(1, arg)
  select case (trim(arg))
  case ("--version", "-v")
    print '(a)', "MEMDIF3D " // VERSION // " (" // BUILD_TYPE // ")"
  case ("--help", "-h")
    call print_usage()
  case default
    write (*, '(a)') "memdif3d: running a simulation from '" // trim(arg) // "' is not implemented yet."
    error stop 2
  end select

contains

  subroutine print_usage()
    print '(a)', "MEMDIF3D " // VERSION
    print '(a)', "Usage: memdif3d <namefile>"
    print '(a)', "       memdif3d --version | --help"
  end subroutine print_usage

end program memdif3d
