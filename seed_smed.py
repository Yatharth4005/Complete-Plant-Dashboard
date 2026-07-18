import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import Department
from smed.models import SMEDTemplate, SMEDSubActivityConfig

def seed_smed():
    departments = Department.objects.all()
    if not departments.exists():
        print("No departments found in the database!")
        return

    templates_data = [
        {
            "name": "SMED EAF SHELL CHANGE",
            "code": "EAF_SHELL_CHANGE",
            "activities": [
                {
                    "group_name": "Pre Operational Activity of Delta & Shell Change (48 Minutes)",
                    "sub_activities": [
                        ("Furnace Power Off", 0, "PRASHANT"),
                        ("Electrode 3 Removal Before Tapping", 3, ""),
                        ("Last Heat Tapped In 1 St Ladle", 4, ""),
                        ("Electrode 1 And 2 Removal", 5, ""),
                        ("2nd Ladle Tapping", 8, ""),
                        ("Bottom Lancing", 10, ""),
                        ("Take Furnace at Level position", 5, ""),
                        ("Gantry Swing & Shell Bolts Opening", 13, "")
                    ]
                },
                {
                    "group_name": "Main Shell Change Operation (180 Minutes)",
                    "sub_activities": [
                        ("Shell lifting & placing on transfer car", 20, ""),
                        ("New Shell shifting & centering", 30, ""),
                        ("Shell bolt tightening & locking", 40, ""),
                        ("Roof centering & locking", 30, ""),
                        ("Electrode installation & alignment", 30, ""),
                        ("Water connection & system checks", 30, "")
                    ]
                },
                {
                    "group_name": "Post Operational System Checks (124 Minutes)",
                    "sub_activities": [
                        ("Cold trial of hydraulic & gantry rotation", 24, ""),
                        ("Power on & first heat testing", 60, ""),
                        ("Final inspection & signoff", 40, "")
                    ]
                }
            ]
        },
        {
            "name": "SMED COMBI SECTION CHANGE FROM ROUND TO BLOOM",
            "code": "COMBI_CAST_STRAND_CHANGE",
            "activities": [
                {
                    "group_name": "1) Pre Operational Activity of section change (35 Minutes)",
                    "sub_activities": [
                        ("Replacement of Mould Top Plate", 5, ""),
                        ("Removal of Mould Cover", 5, ""),
                        ("Mould and Machine Cooling Pump Off", 5, ""),
                        ("Spray Cooling Pump Off", 5, ""),
                        ("Ems Pump Off", 5, ""),
                        ("Mould Cooling Valve Closing", 10, "")
                    ]
                },
                {
                    "group_name": "2) Section Change Activity (360 Minutes)",
                    "sub_activities": [
                        ("Fixing of life line around the top floor", 10, ""),
                        ("Mould bolt remove", 15, ""),
                        ("Segment hoses connection remove", 15, ""),
                        ("Mould remove", 15, ""),
                        ("EMS Hoses remove", 15, ""),
                        ("EMS remove", 15, ""),
                        ("Segment remove", 20, ""),
                        ("Segment Placement", 25, ""),
                        ("Segment hoses connection", 20, ""),
                        ("Zone-4 spray header replacement", 20, ""),
                        ("Zone-4 air hose connection", 15, ""),
                        ("Spray water flashing", 15, ""),
                        ("Spray cooling hose connection (zone-1,2 & 3)", 20, ""),
                        ("Zone wise spray checking", 15, ""),
                        ("EMS placement", 20, ""),
                        ("Mould placement", 25, ""),
                        ("Mould bolt tightening", 15, ""),
                        ("Mould cooling valve opening", 15, ""),
                        ("Mould cooling pump start & leakage checking", 20, ""),
                        ("Counter fixing", 10, ""),
                        ("Crane no 200 taken by billet for tundish shifting", 10, ""),
                        ("Crane no 200 taken by billet for tundish shifting", 10, "")
                    ]
                }
            ]
        },
        {
            "name": "SMED EBT Repair",
            "code": "SHELL_CHANGE_OVER",
            "activities": [
                {
                    "group_name": "Preparation Phase",
                    "sub_activities": [
                        ("Pre-heating of tooling", 30, ""),
                        ("Crane readiness check", 15, "")
                    ]
                },
                {
                    "group_name": "Shell Swap",
                    "sub_activities": [
                        ("Old shell disconnect", 45, ""),
                        ("Swap operations", 60, ""),
                        ("New shell secure", 45, "")
                    ]
                }
            ]
        },
        {
            "name": "SMED BILLET SECTION CHANGE FROM BLOOM TO ROUND",
            "code": "CC_SECTION_CHANGE",
            "activities": [
                {
                    "group_name": "1) Pre Operational Activity of section change (35 Minutes)",
                    "sub_activities": [
                        ("Replacement of Mould Top Plate", 5, ""),
                        ("Removal of Mould Cover", 5, ""),
                        ("Mould and Machine Cooling Pump Off", 5, ""),
                        ("Spray Cooling Pump Off", 5, ""),
                        ("Ems Pump Off", 5, ""),
                        ("Mould Cooling Valve Closing", 10, "")
                    ]
                },
                {
                    "group_name": "2) Section Change Activity (360 Minutes)",
                    "sub_activities": [
                        ("Fixing of life line around the top floor", 10, ""),
                        ("Mould bolt remove", 15, ""),
                        ("Segment hoses connection remove", 15, ""),
                        ("Mould remove", 20, ""),
                        ("EMS remove", 20, ""),
                        ("Segment remove", 25, ""),
                        ("Segment Placement", 30, ""),
                        ("Segment hoses connection", 25, ""),
                        ("Zone-4 spray header replacement", 20, ""),
                        ("Zone-4 air hose connection", 15, ""),
                        ("Spray water flashing", 15, ""),
                        ("Spray cooling hose connection (zone-1,2 & 3)", 20, ""),
                        ("Zone wise spray checking", 15, ""),
                        ("EMS placement", 20, ""),
                        ("Mould placement", 25, ""),
                        ("Mould bolt tightening", 15, ""),
                        ("Mould cooling valve opening", 15, ""),
                        ("Mould cooling pump start & leakage checking", 20, ""),
                        ("Crane no 200 taken by billet for tundish shifting", 10, ""),
                        ("Crane no 200 taken by billet for tundish shifting", 10, "")
                    ]
                }
            ]
        }
    ]

    # Create templates and configs for each department
    for dept in departments:
        print(f"\nSeeding templates for Department: {dept.name} ({dept.code})")
        for t_data in templates_data:
            template, created = SMEDTemplate.objects.get_or_create(
                department=dept,
                code=t_data["code"],
                defaults={"name": t_data["name"]}
            )
            if not created:
                template.name = t_data["name"]
                template.save()
            if created:
                print(f"  [+] Created SMED Template: '{template.name}'")
            else:
                print(f"  [*] Template '{template.name}' already exists.")
                # Clear old configs to prevent duplicates
                template.sub_activities.all().delete()

            # Seed configs
            order_idx = 0
            for group in t_data["activities"]:
                group_name = group["group_name"]
                for sub_name, duration, resp in group["sub_activities"]:
                    SMEDSubActivityConfig.objects.create(
                        template=template,
                        group_name=group_name,
                        name=sub_name,
                        default_planned_duration_mins=duration,
                        default_responsibility=resp,
                        order=order_idx
                    )
                    order_idx += 1
            print(f"    └─ Seeded {order_idx} subactivities.")

    print("\nSMED Templates seeding completed successfully for all departments!")

if __name__ == "__main__":
    seed_smed()
