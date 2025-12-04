from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import *
from .serializers import *
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q



from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.views import APIView
from datetime import timedelta

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from datetime import datetime





class LeadViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Items.
    Provides CRUD operations automatically.
    """
    queryset = Lead.objects.all().order_by('-created_at')
    serializer_class = LeadSerializer




class OutreachViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Outreach Sequences.
    """
    queryset = OutreachSequence.objects.all().order_by('-sent_at')
    serializer_class = OutreachSequenceSerializer

    def list(self, request, *args, **kwargs):
        sequences = OutreachSequence.objects.all().order_by('-sent_at')
        response_data = []

        for seq in sequences:
            lead = seq.lead
            # Get the latest tracking event for this sequence
            latest_event = OutreachTracking.objects.filter(sequence=seq).order_by('-timestamp').first()

            events = OutreachTracking.objects.filter(sequence=seq)

            # Optional: count of opens, clicks, replies, bounces for this sequence
            tracking_counts = OutreachTracking.objects.filter(sequence=seq).values('event').annotate(count=Count('id'))

            event_counts = {tc['event']: tc['count'] for tc in tracking_counts}

            response_data.append({
                "id": seq.id,
                "lead": lead.id,
                "lead_name": lead.name,
                "lead_business": lead.company_name,
                "lead_email": lead.email,
                "step": seq.step,
                "status": seq.status,
                "email_subject": seq.email_subject,
                "email_body": seq.email_body,
                "sent_at": seq.sent_at,
                "response_at": seq.response_at,
                "event": latest_event.event if latest_event else None,  # latest event
                "event_counts": event_counts,  # counts for frontend
                "opened": events.filter(event="opened").exists(),
                "clicked": events.filter(event="clicked").exists(),
                "replied": events.filter(event="replied").exists(),
                "bounced": events.filter(event="bounced").exists(),
            })

        return Response(response_data)

    @action(detail=False, methods=["get"])
    def metrics(self, request):
        """
        Returns aggregated outreach metrics.
        """
        total_sent = OutreachSequence.objects.filter(status='sent').count()
        total_replied = OutreachSequence.objects.filter(status='responded').count()

        # Aggregating tracking events
        tracking_counts = OutreachTracking.objects.aggregate(
            opened=Count('id', filter=Q(event='opened')),
            replied=Count('id', filter=Q(event='replied')),
            bounced=Count('id', filter=Q(event='bounced'))
        )

        metrics = {
            "total_sent": total_sent,
            "opened": tracking_counts.get('opened', 0),
            "replied": tracking_counts.get('replied', 0),
            "bounced": tracking_counts.get('bounced', 0) + OutreachSequence.objects.filter(status='failed').count(),
        }

        return Response(metrics)




def get_followups_sent(time_range="today"):
    now = timezone.now()

    if time_range == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "week":
        start = now - timedelta(days=now.weekday())  # Monday
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = None

    queryset = OutreachSequence.objects.filter(step__gt=1, status="sent")

    followups_sent_count = queryset.count()
    print(followups_sent_count)
    return followups_sent_count





class DashboardMetricsAPIView(APIView):
    def get(self, request):
        time_range = request.GET.get("timeRange", "today")
        now = timezone.now()

        if time_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # week
            start = now - timedelta(days=7)

        total_leads_sourced = Lead.objects.filter(created_at__gte=start).count()
        emails_sent = OutreachSequence.objects.filter(sent_at__gte=start).count()
        open_count = OutreachTracking.objects.filter(event='opened', timestamp__gte=start).count()
        reply_count = OutreachTracking.objects.filter(event='replied', timestamp__gte=start).count()

        # You can add more metrics here
        data = {
            "total_leads_sourced": total_leads_sourced,
            "emails_sent": emails_sent,
            "open_count": open_count,
            "reply_count": reply_count,
            "followups_sent": get_followups_sent(time_range),

        }

        return Response(data)





from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import OutreachSequence, Lead

@api_view(['GET'])
def followup_metrics(request):
    """
    Returns metrics for follow-ups based on timeRange query param (today/week)
    """
    time_range = request.GET.get("timeRange", "today")
    now = timezone.now()

    # Determine start datetime for filtering
    if time_range == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "week":
        start = now - timedelta(days=now.weekday())  # Monday
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = None

    # Filter sent follow-ups
    queryset = OutreachSequence.objects.filter(step__gt=1, status="sent")

    total_followups_sent = queryset.count()

    # Replies
    replied_qs = queryset.filter(status="responded")
    followup_reply_rate = round((replied_qs.count() / total_followups_sent) * 100, 1) if total_followups_sent else 0

    # Average time to reply
    reply_times = [ (f.response_at - f.sent_at).total_seconds() for f in replied_qs if f.response_at and f.sent_at ]
    avg_reply_time_seconds = sum(reply_times) / len(reply_times) if reply_times else 0
    avg_reply_time = f"{round(avg_reply_time_seconds/3600, 1)}h"  # hours

    # Best follow-up step
    steps = queryset.values_list("step", flat=True).distinct()
    best_step = 1
    best_rate = 0
    for step in steps:
        step_qs = queryset.filter(step=step)
        if step_qs.count() == 0:
            continue
        step_reply_qs = step_qs.filter(status="responded")
        step_rate = (step_reply_qs.count() / step_qs.count()) * 100
        if step_rate > best_rate:
            best_rate = step_rate
            best_step = step

    # Leads needing follow-up (sent but no reply)
    leads_needing_followup = queryset.filter(status="sent").count()

    # Overdue (optional: more than 24h since sent)
    overdue_followups = queryset.filter(sent_at__lte=now - timedelta(hours=24), status="sent").count()

    data = {
        "total_followups_sent": total_followups_sent,
        "followup_reply_rate": followup_reply_rate,
        "avg_reply_time": avg_reply_time,
        "best_followup_step": best_step,
        "best_followup_rate": round(best_rate, 1),
        "leads_needing_followup": leads_needing_followup,
        "overdue_followups": overdue_followups,
        "followups_sent_trend": "+22% from last week",  # Optional: implement real trend calculation
        "reply_rate_trend": "+4% avg",
        "avg_reply_time_trend": "-0.5h faster",
        "best_followup_trend": "+3% vs avg"
    }

    return Response(data)





class FollowUpsAPIView(APIView):
    def get(self, request):
        time_range = request.GET.get("timeRange", "today")
        now = timezone.now()

        if time_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == "week":
            start = now - timedelta(days=now.weekday())  # Monday
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start = None

        queryset = OutreachSequence.objects.filter(step__gt=1)  # follow-up steps


        data = [
            {
                "id": fu.id,
                "name": fu.lead.name,
                "lastContact": fu.sent_at.strftime("%Y-%m-%d") if fu.sent_at else "N/A",
                "step": f"Follow-Up {fu.step}",
                "suggestedDate": (fu.sent_at + timedelta(days=2)).strftime("%Y-%m-%d") if fu.sent_at else "N/A",
                "status": fu.status,
            }
            for fu in queryset
        ]

        return Response(data)




# -----------------------------
# Inbound replies webhook
# -----------------------------
@csrf_exempt
def mailgun_inbound_webhook(request):
    if request.method == "POST":
        message_id = request.POST.get("In-Reply-To") or request.POST.get("Message-Id")
        from_email = request.POST.get("From")
        body = request.POST.get("body-plain")

        print("📩 Incoming reply webhook received")
        print(f"Message ID: {message_id}")
        print(f"From: {from_email}")
        print(f"Body: {body}")

        # Match to original email sent
        tracking = OutreachTracking.objects.filter(message_id=message_id).first()
        if tracking:
            tracking.event = "replied"
            tracking.reply_body = body
            tracking.save()
            print(f"✅ Reply recorded for {tracking.lead.email}")
        else:
            print("⚠️ No matching tracking record found")

    return HttpResponse("ok")


# -----------------------------
# Event webhook (opened, clicked, etc.)
# -----------------------------
@csrf_exempt
# -----------------------------
@csrf_exempt
def mailgun_event_webhook(request):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    try:
        data = json.loads(request.body)
        print("📢 Mailgun event webhook triggered")
    except Exception as e:
        print(f"❌ Failed to parse JSON: {e}")
        return HttpResponse("bad request", status=400)

    event_data = data.get("event-data", {})
    event = event_data.get("event")
    raw_message_id = event_data.get("message", {}).get("headers", {}).get("message-id")

    if not raw_message_id:
        print("⚠️ No message-id found in webhook")
        return HttpResponse("ok")

    print(f"Event type: {event}")
    print(f"Raw message ID: {raw_message_id}")

    # Normalize message_id to handle angle brackets
    normalized_ids = [raw_message_id, f"<{raw_message_id}>", raw_message_id.strip("<>")]

    # First try to match OutreachTracking
    tracking = OutreachTracking.objects.filter(message_id__in=normalized_ids).first()
    if tracking:
        if event == "opened":
            tracking.event = "opened"
            tracking.opened_at = timezone.now()
        elif event == "replied":
            tracking.event = "replied"
            tracking.replied_at = timezone.now()
        elif event == "bounced":
            tracking.event = "bounced"
        tracking.save()
        print(f"✅ Event '{event}' recorded for OutreachTracking lead {tracking.lead.email}")
        return HttpResponse("ok")

    # Then try to match FollowUp
    followup = FollowUp.objects.filter(message_id__in=normalized_ids).first()
    if followup:
        if event == "opened":
            followup.opened = True
            followup.opened_at = timezone.now()
        elif event == "replied":
            followup.status = "replied"
            followup.replied_at = timezone.now()
        elif event == "bounced":
            followup.status = "bounced"
        followup.save()
        print(f"✅ Event '{event}' recorded for FollowUp #{followup.followup_number} lead {followup.lead.email}")
        return HttpResponse("ok")

    print("⚠️ No matching record found for message ID")
    return HttpResponse("ok")

@api_view(['GET'])
def health_check(request):
    """Simple health check endpoint."""
    return Response({
        'status': 'healthy',
        'message': 'API is running'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def ping(request):
    """Ping endpoint for quick checks."""
    return Response({'message': 'pong'}, status=status.HTTP_200_OK)



