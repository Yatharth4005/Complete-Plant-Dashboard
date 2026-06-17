# Generated manually to seed default governance assignments

from django.db import migrations
from django.contrib.auth.hashers import make_password

def seed_governance_data(apps, schema_editor):
    User = apps.get_model('tpm', 'User')
    TPMGovernanceAssignment = apps.get_model('tpm', 'TPMGovernanceAssignment')
    
    # Define data to seed
    # format: (name, role_key, designation)
    data = [
        # Chairman
        ("Anshoo Raina", "chairman", "Chairman"),
        # Vice Chairman
        ("Lalit Goyal", "vice_chairman", "HOD"),
        # Committee Members
        ("Amit Khokhar", "committee_member", "Committee Member"),
        ("Ankit Bansal", "committee_member", "Committee Member"),
        ("Praveen George", "committee_member", "Committee Member"),
        ("Pinaki Bhattacharjee", "committee_member", "Committee Member"),
        ("Moreshwar Borkar", "committee_member", "Committee Member"),
        ("Pradeep Kumar Agrawal", "committee_member", "Committee Member"),
        ("Sanjay Sharma", "committee_member", "Committee Member"),
        # TPM Coordinators
        ("Raj Bhushan", "coordinator_pillar", "Pillar Coordinator"),
        ("Raunika", "coordinator_cell", "Cell Team Coordinator"),
        # HOD / Area Owners
        ("Sandeep Tyagi", "hod", "HOD"),
        ("Saptarsi Sengupta", "hod", "HOD"),
        ("Varun Mishra", "hod", "HOD"),
        ("Satyabrata Sahu", "hod", "HOD"),
        ("Harsh Pandey", "hod", "HOD"),
        ("Gunjan Jha", "hod", "HOD"),
        ("Ch VSS Kumar", "hod", "HOD"),
        ("Deepak Upadhyay", "hod", "HOD"),
        ("Pawan Vij", "hod", "HOD"),
    ]
    
    for idx, (full_name, role_key, designation) in enumerate(data):
        # Split full name into first and last
        parts = full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
        
        # Look for existing user
        user = None
        if full_name == "Lalit Goyal":
            # Search by first/last name
            user = User.objects.filter(first_name="Lalit", last_name="Goyal").first()
            if not user:
                user = User.objects.filter(email="lalit.goyal@jindalsteel.in").first()
        
        if not user:
            # Generate username
            username = full_name.lower().replace(" ", ".")
            # Make sure username is unique
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
                
            email = f"{username}@jindalsteel.in"
            
            # Create user with hashed password
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                designation=designation,
                password=make_password("Jspl@123"),
                is_active=True
            )
        else:
            # Update designation if not set
            if not user.designation:
                user.designation = designation
                user.save()
                
        # Create assignment
        TPMGovernanceAssignment.objects.get_or_create(
            role_key=role_key,
            user=user,
            defaults={'sort_order': idx}
        )

def rollback_governance_data(apps, schema_editor):
    TPMGovernanceAssignment = apps.get_model('tpm', 'TPMGovernanceAssignment')
    TPMGovernanceAssignment.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ("tpm", "0009_tpmgovernanceassignment"),
    ]

    operations = [
        migrations.RunPython(seed_governance_data, rollback_governance_data),
    ]
