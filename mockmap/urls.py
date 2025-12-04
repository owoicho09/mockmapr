from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

# Router automatically maps ViewSets to REST endpoints
router = DefaultRouter()
router.register(r'leads', LeadViewSet, basename='lead')
router.register(r'outreach', OutreachViewSet, basename='outreach')

urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('ping/', ping, name='ping'),
    path('', include(router.urls)),
    path("dashboard/metrics/", DashboardMetricsAPIView.as_view(), name="dashboard-metrics"),
    path('followups/metrics/', followup_metrics, name='followup-metrics'),
    path('followups/', FollowUpsAPIView.as_view(), name='followups'),

    # Inbound replies webhook
    path('webhooks/mailgun/inbound/', mailgun_inbound_webhook, name='mailgun_inbound_webhook'),

    # Event webhook (opens, clicks, etc.)
    path('webhooks/mailgun/events/', mailgun_event_webhook, name='mailgun_event_webhook'),

]
