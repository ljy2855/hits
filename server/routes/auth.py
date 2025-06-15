from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
import httpx
import os
from typing import Optional
from ..config.settings import settings

router = APIRouter()

GITHUB_CLIENT_ID = settings.GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET = settings.GITHUB_CLIENT_SECRET
GITHUB_CALLBACK_URL = settings.GITHUB_CALLBACK_URL

# httpx 클라이언트 설정
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
CLIENT = httpx.AsyncClient(timeout=TIMEOUT)

@router.get("/github")
async def github_login():
    """GitHub OAuth 로그인 시작"""
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={GITHUB_CALLBACK_URL}"
    )

@router.get("/github/callback")
async def github_callback(code: str, response: Response):
    """GitHub OAuth 콜백 처리"""
    try:
        # 액세스 토큰 요청
        token_response = await CLIENT.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get access token: {token_response.text}"
            )
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="No access token received"
            )
        
        # 사용자 정보 요청
        user_response = await CLIENT.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/json",
            },
        )
        
        if user_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get user info: {user_response.text}"
            )
        
        user_data = user_response.json()
        
        # 세션에 사용자 정보와 액세스 토큰 저장
        response = RedirectResponse(url="/")
        response.set_cookie(
            key="github_user",
            value=user_data["login"],
            httponly=True,
            max_age=3600 * 24 * 7,  # 7일
        )
        response.set_cookie(
            key="github_token",
            value=access_token,
            httponly=True,
            max_age=3600 * 24 * 7,  # 7일
        )
        
        return response
        
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Connection to GitHub timed out. Please try again."
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to GitHub: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/status")
async def auth_status(request: Request):
    """현재 인증 상태 확인"""
    github_user = request.cookies.get("github_user")
    github_token = request.cookies.get("github_token")
    
    if not github_user or not github_token:
        print("No github_user or github_token cookie found")  # 디버깅용 로그
        return {"authenticated": False}
    
    try:
        print(f"Fetching user info for: {github_user}")  # 디버깅용 로그
        user_response = await CLIENT.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/json",
            },
        )
        
        
        if user_response.status_code != 200:
            print(f"GitHub API error: {user_response.text}")  # 디버깅용 로그
            return {"authenticated": False}
        
        user_data = user_response.json()
        
        return {
            "authenticated": True,
            "login": user_data["login"],
            "avatar_url": user_data["avatar_url"],
        }
    except Exception as e:
        print(f"Error in auth_status: {str(e)}")  # 디버깅용 로그
        return {"authenticated": False}

@router.get("/logout")
async def logout(response: Response):
    """로그아웃"""
    response = RedirectResponse(url="/")
    response.delete_cookie("github_user")
    response.delete_cookie("github_token")
    return response 