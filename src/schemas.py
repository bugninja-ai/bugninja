from typing import Any, Dict, List, Optional

from browser_use.agent.views import AgentBrain  # type: ignore
from browser_use.browser import BrowserProfile  # type: ignore
from browser_use.browser.profile import (  # type: ignore
    ClientCertificate,
    ColorScheme,
    Geolocation,
    ProxySettings,
    ViewportSize,
)
from pydantic import BaseModel, Field, NonNegativeFloat

#! State comparisons


class ElementComparison(BaseModel):
    index: int
    reason: str
    equals: bool


class StateComparison(BaseModel):
    evaluation: List[ElementComparison]


#! Traversal


class BugninjaBrowserConfig(BaseModel):
    user_agent: Optional[str] = Field(default=None)
    viewport: Optional[Dict[str, int]] = Field(default=None)
    device_scale_factor: Optional[NonNegativeFloat] = Field(default=None)
    color_scheme: ColorScheme = Field(default=ColorScheme.LIGHT)
    accept_downloads: bool = Field(default=False)
    proxy: Optional[ProxySettings] = Field(default=None)
    client_certificates: List[ClientCertificate] = Field(default_factory=list)
    extra_http_headers: Dict[str, str] = Field(default_factory=dict)
    http_credentials: Optional[Dict[str, str]] = Field(default=None)
    java_script_enabled: bool = Field(default=True)
    geolocation: Optional[Geolocation] = Field(default=None)
    timeout: float = Field(default=30_000)
    headers: Optional[Dict[str, str]] = Field(default=None)
    allowed_domains: Optional[List[str]] = Field(default=None)

    @staticmethod
    def from_browser_profile(browser_profile: BrowserProfile) -> "BugninjaBrowserConfig":

        viewport: Optional[ViewportSize] = browser_profile.viewport
        viewport_element: Optional[Dict[str, int]] = None

        if viewport is not None:
            viewport_element = {
                "width": viewport.width,
                "height": viewport.height,
            }

        return BugninjaBrowserConfig(
            user_agent=browser_profile.user_agent,
            viewport=viewport_element,
            device_scale_factor=browser_profile.device_scale_factor,
            color_scheme=browser_profile.color_scheme,
            accept_downloads=browser_profile.accept_downloads,
            proxy=browser_profile.proxy,
            client_certificates=browser_profile.client_certificates,
            extra_http_headers=browser_profile.extra_http_headers,
            http_credentials=browser_profile.http_credentials,
            java_script_enabled=browser_profile.java_script_enabled,
            geolocation=browser_profile.geolocation,
            timeout=browser_profile.timeout,
            headers=browser_profile.headers,
            allowed_domains=browser_profile.allowed_domains,
        )


class BugninjaExtendedAction(BaseModel):
    brain_state_id: str
    action: Dict[str, Any]
    dom_element_data: Optional[Dict[str, Any]]


class Traversal(BaseModel):
    test_case: str
    browser_config: BugninjaBrowserConfig
    secrets: Dict[str, str]
    brain_states: Dict[str, AgentBrain]
    actions: Dict[str, BugninjaExtendedAction]

    class Config:
        arbitrary_types_allowed = True
