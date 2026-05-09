"""Rutas de autenticación: /api/auth/{login,me,logout}."""
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.deps import get_current_user
from app.auth.provider import get_auth_provider
from app.models.user import LoginRequest, LoginResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    provider = get_auth_provider()
    user = await provider.authenticate(payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = await provider.issue_token(user)
    return LoginResponse(access_token=token, token_type="bearer", user=user)


@router.get("/me", response_model=UserPublic)
async def me(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> Response:
    # Stateless: el cliente descarta el token. Simbólico.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
