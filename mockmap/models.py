from django.db import models





class OutreachTemplate(models.Model):
    name = models.CharField(max_length=255)  # e.g. "Warm Opener", "Bump", "Breakup"
    step = models.IntegerField()  # 1,2,3,4
    subject = models.CharField(max_length=255)
    body = models.TextField()
    version = models.CharField(max_length=50, default="v1")  # A/B tests

    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['step']


class Lead(models.Model):
    SOURCE_CHOICES = [
        ('google_maps', 'Google Maps'),
        ('apollo', 'Apollo'),
    ]

    company_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255,null=True,blank=True)

    website = models.CharField(max_length=255, null=True, blank=True)
    address = models.CharField(max_length=50,null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    keywords = models.TextField(null=True, blank=True)
    linkedin_url = models.CharField(max_length=100,null=True, blank=True)

    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    # Lead meta
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    rating = models.FloatField(null=True, blank=True)
    reviews_count = models.IntegerField(null=True, blank=True)

    # Verification
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    scored = models.BooleanField(default=False)
    icp_match = models.BooleanField(default=False)
    icp_reason = models.TextField(null=True, blank=True)


    # Tracking
    email_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    apollo_id = models.CharField(max_length=255,null=True,blank=True)

    class Meta:
        ordering = ['-created_at']


class LeadStatus(models.Model):
    lead = models.OneToOneField(Lead, on_delete=models.CASCADE, related_name="status")

    scraped = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    enriched = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)
    last_update = models.DateTimeField(auto_now=True)


class Template(models.Model):
    TEMPLATE_TYPE_CHOICES = [
        ('first_touch', 'First Touch'),
        ('follow_up', 'Follow Up'),
        ('follow_up_2', 'Follow Up 2'),
        ('case_study', 'Case Study'),
        ('no-opened-follow_up', 'Not Opened')

    ]

    name = models.CharField(max_length=100, blank=True, null=True)  # Optional for easy identification
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES,default='first_touch')
    sequence_order = models.PositiveIntegerField(default=1)
    content = models.TextField(help_text="Email or outreach template text")

    is_active = models.BooleanField(default=True)


    def __str__(self):
        return self.name


class OutreachSequence(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    step = models.IntegerField(default=1)
    template = models.ForeignKey(OutreachTemplate, on_delete=models.SET_NULL, null=True,blank=True)
    template_used = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True,blank=True)

    email_subject = models.CharField(max_length=255)
    email_body = models.TextField()

    status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('failed', 'Failed'),
            ('responded', 'Responded'),
        ],
        default='pending'
    )


    sent_at = models.DateTimeField(null=True, blank=True)
    response_at = models.DateTimeField(null=True, blank=True)



class OutreachTracking(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    sequence = models.ForeignKey(OutreachSequence, on_delete=models.CASCADE,null=True,blank=True)

    event = models.CharField(
        max_length=50,
        choices=[
            ('delivered', 'Delivered'),
            ('opened', 'Opened'),
            ('clicked', 'Clicked'),
            ('replied', 'Replied'),
            ('bounced', 'Bounced'),
            ('pending', 'Pending'),

        ],null=True,blank=True
    )
    message_id = models.CharField(max_length=255, null=True, blank=True)  # Mailgun ID
    opened_at = models.DateTimeField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True,null=True,blank=True)





class FollowUp(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ready', 'Ready for Send'),
        ('sent', 'Sent'),
        ('replied', 'Replied'),
        ('bounced', 'Bounced'),
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='followups'
    )
    parent_email = models.ForeignKey(
        OutreachTracking,
        on_delete=models.CASCADE,
        related_name='followup_emails',
        null=True,
        blank=True
    )

    # NEW — so script can store which template was used
    template = models.ForeignKey(
        Template,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    followup_number = models.PositiveIntegerField(default=1)
    template_type = models.CharField(max_length=50, blank=True)  # follow_up, case_study...

    # Script expects these:
    email_subject = models.CharField(max_length=255, blank=True)
    email_body = models.TextField(blank=True)

    # NEW — script sets this when scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    ready_for_followup = models.BooleanField(default=False)
    opened = models.BooleanField(default=False)

    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    message_id = models.CharField(max_length=255, null=True, blank=True)  # Mailgun ID


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['lead', 'followup_number']
        verbose_name = 'Follow Up'
        verbose_name_plural = 'Follow Ups'

    def __str__(self):
        return f"Follow-up #{self.followup_number} for {self.lead.email}"

    @property
    def is_ready_to_send(self):
        return self.ready_for_followup and self.status in ['draft', 'ready']











