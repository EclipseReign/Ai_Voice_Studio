""""
Security Middleware for FastAPI Application
============================================

This module provides comprehensive security features:
- Rate limiting (DDoS protection)
- Security headers (XSS, CSRF, etc)
- Input validation and sanitization
- Audit logging
- NoSQL injection prevention
"""

import logging
import re
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)

# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """
    In-memory rate limiter with sliding window algorithm
    
    Limits:
    - Anonymous: 100 requests per 15 minutes
    - Authenticated: 1000 requests per 15 minutes
    - Per endpoint stricter limits for expensive operations
    """
    
    def __init__(self):
        # Storage: {identifier: [(timestamp, endpoint), ...]}
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = asyncio.Lock()
        
        # Rate limits (requests per window)
        self.ANONYMOUS_LIMIT = 100
        self.AUTHENTICATED_LIMIT = 1000
        self.WINDOW_SECONDS = 900  # 15 minutes
        
        # Stricter limits for expensive endpoints
        self.ENDPOINT_LIMITS = {
            "/api/text/generate-with-progress": 20,  # LLM generation
            "/api/audio/synthesize-with-progress": 30,  # Audio synthesis
            "/api/video/generate-with-progress": 10,  # Video generation
        }
        
        logger.info("Rate limiter initialized")
    
    async def check_rate_limit(self, identifier: str, endpoint: str, is_authenticated: bool = False) -> bool:
        """
        Check if request is within rate limits
        
        Returns: True if allowed, False if rate limited
        """
        async with self.lock:
            now = time.time()
            cutoff = now - self.WINDOW_SECONDS
            
            # Clean old requests
            self.requests[identifier] = [
                (ts, ep) for ts, ep in self.requests[identifier]
                if ts > cutoff
            ]
            
            # Count requests in current window
            total_requests = len(self.requests[identifier])
            endpoint_requests = sum(1 for _, ep in self.requests[identifier] if ep == endpoint)
            
            # Check global limit
            limit = self.AUTHENTICATED_LIMIT if is_authenticated else self.ANONYMOUS_LIMIT
            if total_requests >= limit:
                logger.warning(f"Rate limit exceeded for {identifier} (global limit: {limit})")
                return False
            
            # Check endpoint-specific limit
            if endpoint in self.ENDPOINT_LIMITS:
                endpoint_limit = self.ENDPOINT_LIMITS[endpoint]
                if endpoint_requests >= endpoint_limit:
                    logger.warning(
                        f"Endpoint rate limit exceeded for {identifier} on {endpoint} "
                        f"({endpoint_requests}/{endpoint_limit})"
                    )
                    return False
            
            # Add current request
            self.requests[identifier].append((now, endpoint))
            return True
    
    async def cleanup_old_entries(self):
        """Background task to cleanup old entries (memory optimization)"""
        while True:
            await asyncio.sleep(3600)  # Run every hour
            async with self.lock:
                now = time.time()
                cutoff = now - self.WINDOW_SECONDS
                
                # Remove identifiers with no recent requests
                to_remove = []
                for identifier, requests in self.requests.items():
                    cleaned = [(ts, ep) for ts, ep in requests if ts > cutoff]
                    if cleaned:
                        self.requests[identifier] = cleaned
                    else:
                        to_remove.append(identifier)
                
                for identifier in to_remove:
                    del self.requests[identifier]
                
                logger.info(f"Rate limiter cleanup: {len(to_remove)} identifiers removed")


# Global rate limiter instance
rate_limiter = RateLimiter()


# ============================================================================
# INPUT SANITIZATION & VALIDATION
# ============================================================================

class InputSanitizer:
    """Sanitize and validate user inputs to prevent injection attacks"""
    
    # Dangerous patterns for NoSQL injection
    NOSQL_INJECTION_PATTERNS = [
        r'$where',
        r'$ne',
        r'$gt',
        r'$gte',
        r'$lt',
        r'$lte',
        r'$in',
        r'$nin',
        r'$regex',
        r'$exists',
        r'$type',
        r'$expr',
        r'$jsonSchema',
        r'$mod',
        r'$text',
        r'$all',
        r'$elemMatch',
        r'$size',
    ]
    
    # SQL injection patterns (just in case)
    SQL_INJECTION_PATTERNS = [
        r'unions+select',
        r'drops+table',
        r'deletes+from',
        r'inserts+into',
        r'updates+.*set',
        r'execs*\(',
        r'executes*\(',
        r'scripts*>',
    ]
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 10000) -> str:
        """
        Sanitize string input
        - Remove potentially dangerous characters
        - Limit length
        - Check for injection patterns
        """
        if not isinstance(value, str):
            return str(value)
        
        # Limit length
        if len(value) > max_length:
            logger.warning(f"Input truncated from {len(value)} to {max_length} chars")
            value = value[:max_length]
        
        # Check for NoSQL injection patterns
        for pattern in InputSanitizer.NOSQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.error(f"Potential NoSQL injection detected: {pattern}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input: potentially dangerous pattern detected"
                )
        
        # Check for SQL injection patterns
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.error(f"Potential SQL injection detected: {pattern}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input: potentially dangerous pattern detected"
                )
        
        return value
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any], max_depth: int = 5) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary values
        Prevents nested injection attacks
        """
        if max_depth <= 0:
            logger.warning("Max recursion depth reached in sanitize_dict")
            return {}
        
        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            if not isinstance(key, str):
                continue
            
            # Check for dangerous keys (MongoDB operators)
            if key.startswith('$'):
                logger.error(f"Dangerous key detected: {key}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid key: {key}"
                )
            
            # Sanitize value based on type
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = InputSanitizer.sanitize_dict(value, max_depth - 1)
            elif isinstance(value, list):
                sanitized[key] = [
                    InputSanitizer.sanitize_string(item) if isinstance(item, str)
                    else item
                    for item in value[:100]  # Limit list size
                ]
            else:
                sanitized[key] = value
        
        return sanitized


# ============================================================================
# AUDIT LOGGING
# ============================================================================

class AuditLogger:
    """Log security-relevant events for monitoring and incident response"""
    
    @staticmethod
    async def log_event(
        event_type: str,
        request: Request,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log security event"""
        
        # Get client IP (handle proxy headers)
        client_ip = request.client.host if request.client else "unknown"
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "client_ip": client_ip,
            "user_agent": request.headers.get("User-Agent", "unknown"),
            "endpoint": str(request.url.path),
            "method": request.method,
            "user_id": user_id,
            "details": details or {}
        }
        
        # Log to file (in production, send to SIEM system)
        logger.info(f"SECURITY_EVENT: {log_entry}")
        
        # For critical events, could also:
        # - Send to external monitoring service
        # - Trigger alerts
        # - Store in separate security events database


# ============================================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    
    Headers added:
    - X-Content-Type-Options: nosniff (prevent MIME sniffing)
    - X-Frame-Options: DENY (prevent clickjacking)
    - X-XSS-Protection: 1; mode=block (XSS filter)
    - Strict-Transport-Security: force HTTPS
    - Content-Security-Policy: restrict resource loading
    - Referrer-Policy: control referrer information
    - Permissions-Policy: disable unnecessary browser features
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HSTS (only in production with HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.paypal.com https://www.paypalobjects.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://www.paypal.com https://api-m.sandbox.paypal.com https://api-m.paypal.com; "
            "frame-src https://www.paypal.com https://www.sandbox.paypal.com; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self' https://www.paypal.com;"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (disable unnecessary features)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(self), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=()"
        )
        
        return response


# ============================================================================
# RATE LIMITING MIDDLEWARE
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply rate limiting to all requests"""
    
    EXCLUDED_PATHS = [
        "/",
        "/docs",
        "/openapi.json",
        "/api/health",
        "/api/system/resources"
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Get identifier (user ID or IP address)
        user_id = None
        is_authenticated = False
        
        # Try to get user from cookie
        session_token = request.cookies.get("session_token")
        if session_token:
            # This is simplified - in reality we'd check the session
            user_id = session_token
            is_authenticated = True
        
        # Fallback to IP address
        identifier = user_id or request.client.host if request.client else "unknown"
        
        # Handle proxy headers
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for and not user_id:
            identifier = x_forwarded_for.split(",")[0].strip()
        
        # Check rate limit
        allowed = await rate_limiter.check_rate_limit(
            identifier=identifier,
            endpoint=request.url.path,
            is_authenticated=is_authenticated
        )
        
        if not allowed:
            # Log rate limit violation
            await AuditLogger.log_event(
                event_type="RATE_LIMIT_EXCEEDED",
                request=request,
                user_id=user_id,
                details={
                    "endpoint": request.url.path,
                    "identifier": identifier
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 900  # 15 minutes
                },
                headers={
                    "Retry-After": "900"
                }
            )
        
        return await call_next(request)


# ============================================================================
# SUSPICIOUS ACTIVITY DETECTION
# ============================================================================

class SuspiciousActivityDetector:
    """Detect and log suspicious patterns in requests"""
    
    SUSPICIOUS_PATTERNS = [
        # Common attack patterns
        (r'<script', 'XSS_ATTEMPT'),
        (r'javascript:', 'XSS_ATTEMPT'),
        (r'onerrors*=', 'XSS_ATTEMPT'),
        (r'onclicks*=', 'XSS_ATTEMPT'),
        (r'../../', 'PATH_TRAVERSAL'),
        (r'%2e%2e%2f', 'PATH_TRAVERSAL'),
        (r'etc/passwd', 'PATH_TRAVERSAL'),
        (r'/proc/self', 'PATH_TRAVERSAL'),
        (r'cmd.exe', 'COMMAND_INJECTION'),
        (r'/bin/bash', 'COMMAND_INJECTION'),
        (r'whoami', 'COMMAND_INJECTION'),
    ]
    
    @staticmethod
    async def check_request(request: Request):
        """Check request for suspicious patterns"""
        
        # Check URL
        url_str = str(request.url)
        for pattern, attack_type in SuspiciousActivityDetector.SUSPICIOUS_PATTERNS:
            if re.search(pattern, url_str, re.IGNORECASE):
                await AuditLogger.log_event(
                    event_type=f"SUSPICIOUS_ACTIVITY_{attack_type}",
                    request=request,
                    details={
                        "pattern": pattern,
                        "url": url_str
                    }
                )
                
                logger.warning(f"Suspicious pattern detected: {attack_type} in URL")
        
        # Check headers
        for header_name, header_value in request.headers.items():
            for pattern, attack_type in SuspiciousActivityDetector.SUSPICIOUS_PATTERNS:
                if re.search(pattern, header_value, re.IGNORECASE):
                    await AuditLogger.log_event(
                        event_type=f"SUSPICIOUS_ACTIVITY_{attack_type}",
                        request=request,
                        details={
                            "pattern": pattern,
                            "header": header_name
                        }
                    )
                    
                    logger.warning(f"Suspicious pattern detected: {attack_type} in header {header_name}")


# ============================================================================
# COMBINED SECURITY MIDDLEWARE
# ============================================================================

class SecurityMiddleware(BaseHTTPMiddleware):
    """Combined security middleware for suspicious activity detection"""
    
    async def dispatch(self, request: Request, call_next):
        # Check for suspicious activity
        await SuspiciousActivityDetector.check_request(request)
        
        # Continue with request
        return await call_next(request)