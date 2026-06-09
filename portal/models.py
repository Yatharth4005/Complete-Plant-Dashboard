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
