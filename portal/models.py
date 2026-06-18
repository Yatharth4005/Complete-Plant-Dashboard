from django.db import models
from django.conf import settings
from tpm.models import Department, User

# ─────────────────────────────────────────────
# MODULE REGISTRY
# ─────────────────────────────────────────────
class Module(models.Model):
    key = models.CharField(max_length=30, unique=True) # e.g. 'TPM', 'CMC', 'PRODUCTION'
    label = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    icon = models.CharField(max_length=50, blank=True) # e.g. 'gear', 'chart-bar'
    color_class = models.CharField(max_length=30, blank=True) # e.g. 'module-tpm'
    redirect_url_template = models.CharField(max_length=255) # e.g. 'http://localhost:8001/department/{dept_id}/'
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'label']

    def __str__(self):
        return self.label

# ─────────────────────────────────────────────
# USER ↔ DEPARTMENT ↔ MODULE PERMISSIONS
# ─────────────────────────────────────────────
class UserModuleAccess(models.Model):
    class AccessLevel(models.TextChoices):
        VIEW = 'VIEW', 'View Only'
        EDIT = 'EDIT', 'View + Edit'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='module_access')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='module_access')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='user_access')
    access_level = models.CharField(max_length=10, choices=AccessLevel.choices, default=AccessLevel.EDIT)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='access_grants'
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'department', 'module')
        verbose_name = 'User Module Access'
        verbose_name_plural = 'User Module Accesses'

    def __str__(self):
        return f"{self.user.email} → {self.department.code}/{self.module.key} ({self.access_level})"

# ─────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────
class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100) # e.g. 'LOGIN', 'ACCESS_MODULE', 'LOGOUT'
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    module = models.ForeignKey(Module, null=True, blank=True, on_delete=models.SET_NULL)
    detail = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


# ─────────────────────────────────────────────
# ACCESS SIGN-UP REQUESTS
# ─────────────────────────────────────────────
class AccessRequest(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected')
    ]

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    designation = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Access Request'
        verbose_name_plural = 'Access Requests'

    def __str__(self):
        return f"{self.email} ({self.status})"


# ─────────────────────────────────────────────
# UNIFIED SYSTEM NOTIFICATIONS
# ─────────────────────────────────────────────
class PortalNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portal_notifications')
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"
