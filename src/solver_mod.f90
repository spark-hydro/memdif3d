! One explicit time step. Same order of operations as tools/memdif_proto.py.
module solver_mod
  use kinds_mod, only: dp
  use input_mod, only: model_t
  implicit none
  private
  public :: advance, stability

contains

  subroutine advance(m, cin, cm_in, cout, cm_out)
    type(model_t), intent(in) :: m
    real(dp), intent(in) :: cin(:), cm_in
    real(dp), intent(inout) :: cout(:)
    real(dp), intent(out) :: cm_out
    integer :: k, d, i, p, t
    real(dp) :: u, s, acc

    ! fluid cells read only the old state
    !$omp parallel do default(shared) private(k, d, p, t, u, s)
    do k = 1, m%nf
      p = m%fcell(k)
      u = cin(p)
      s = u
      do d = 1, 6
        t = m%nb(d, k)
        if (t > 0) then
          s = s + m%ks * (cin(t) - u)
        else if (t < 0) then
          s = s + m%km * (cm_in - u)
        end if
      end do
      if (m%advnb(k) > 0) s = s + m%vel * (cin(m%advnb(k)) - u)
      cout(p) = s
    end do
    !$omp end parallel do

    ! source cell
    acc = 0.0_dp
    do i = 1, m%nfaces
      acc = acc + (cm_in - cin(m%face(i)))
    end do
    cm_out = cm_in - m%kmem / m%vol * acc

    ! ghost cells read new values, in file order
    do i = 1, m%ng
      if (m%gsrc(i) > 0) then
        cout(m%gcell(i)) = m%gfac(i) * cout(m%gsrc(i))
      else
        cout(m%gcell(i)) = m%gfac(i)
      end if
    end do
  end subroutine advance

  ! Explicit-scheme limit: for every fluid cell the weights of the new value,
  !   1 - (sum of neighbour coefficients) - velocity,
  ! must stay >= 0, and so must 1 - Km * faces / V for the source cell.
  ! smax is the largest coefficient sum, worst the linear index of that cell, ssrc the source sum.
  subroutine stability(m, smax, worst, ssrc)
    type(model_t), intent(in) :: m
    real(dp), intent(out) :: smax, ssrc
    integer, intent(out) :: worst
    integer :: k, d, t
    real(dp) :: s
    smax = 0.0_dp
    worst = 0
    do k = 1, m%nf
      s = 0.0_dp
      do d = 1, 6
        t = m%nb(d, k)
        if (t > 0) s = s + m%ks
        if (t < 0) s = s + m%km
      end do
      if (m%advnb(k) > 0) s = s + m%vel
      if (s > smax) then
        smax = s
        worst = m%fcell(k)
      end if
    end do
    ssrc = m%kmem * real(m%nfaces, dp) / m%vol
  end subroutine stability

end module solver_mod
