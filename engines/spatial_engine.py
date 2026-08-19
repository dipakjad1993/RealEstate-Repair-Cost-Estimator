"""
Spatial 3D Flaw Mapping Engine (VERIFIED REBUILD)
=================================================
Positions findings on the floor plan deterministically:
- USER_FLOORPLAN: coordinates from an uploaded floorplan / Matterport export
- TEMPLATE: clearly-labeled template layout matched by room name
No random placement.
"""

from datetime import datetime


def create_spatial_map(findings, property_data, user_floorplan=None):
    user_floorplan = user_floorplan or []
    template = _generate_floor_plan(property_data)
    has_user = bool(user_floorplan)
    rooms = user_floorplan if has_user else template
    spatial_items = []
    for finding in findings:
        system = finding.get("system_category", "OTHER")
        location_text = finding.get("location", "")
        room = _match_to_room(location_text, rooms, system)
        zone = _assign_zone(system)
        spatial_items.append({
            "finding_id": finding.get("id"),
            "finding": finding.get("description", "")[:100],
            "severity": finding.get("severity", "MEDIUM"),
            "system": system,
            "room": room.get("name", "Unknown"),
            "wall": _assign_wall(location_text),
            "floor_level": room.get("floor", "Main"),
            "x_position": _center(room, "x", room.get("width", 3)),
            "y_position": _center(room, "y", room.get("height", 2)),
            "zone": zone,
            "color": _severity_color(finding.get("severity", "MEDIUM")),
            "icon": _system_icon(system),
        })
    return {
        "floor_plan": rooms,
        "floor_plan_provenance": "USER_FLOORPLAN" if has_user else "TEMPLATE",
        "floor_plan_note": (
            "Positions from uploaded floorplan/Matterport export."
            if has_user else
            "Template layout derived from beds/baths metadata. Upload a floorplan or "
            "Matterport export on Page 1 for true spatial mapping."
        ),
        "findings_mapped": spatial_items,
        "total_mapped": len(spatial_items),
        "generated_at": datetime.now().isoformat(),
        "severity_legend": {
            "CRITICAL": {"color": "#DC2626", "icon": "red_circle"},
            "HIGH": {"color": "#EA580C", "icon": "orange_circle"},
            "MEDIUM": {"color": "#CA8A04", "icon": "yellow_circle"},
            "LOW": {"color": "#16A34A", "icon": "green_circle"},
        },
        "system_legend": {
            "HVAC": {"icon": "thermometer", "color": "#2563EB"},
            "ROOF": {"icon": "house", "color": "#7C3AED"},
            "ELECTRICAL": {"icon": "bolt", "color": "#F59E0B"},
            "PLUMBING": {"icon": "droplet", "color": "#06B6D4"},
            "STRUCTURAL": {"icon": "building", "color": "#84CC16"},
            "EXTERIOR": {"icon": "tree", "color": "#10B981"},
        },
    }


def _center(room, key, dim):
    pos = room.get(key, 5)
    return round(float(pos), 2)


def _generate_floor_plan(property_data):
    bedrooms = property_data.get("bedrooms", 3)
    bathrooms = property_data.get("bathrooms", 2)
    rooms = [
        {"name": "Living Room", "x": 4, "y": 3, "width": 4, "height": 3, "floor": "Main", "type": "common"},
        {"name": "Kitchen", "x": 8.5, "y": 3, "width": 3, "height": 3, "floor": "Main", "type": "common"},
        {"name": "Dining Room", "x": 4, "y": 7, "width": 3, "height": 2, "floor": "Main", "type": "common"},
        {"name": "Hallway", "x": 8, "y": 6.5, "width": 4, "height": 1, "floor": "Main", "type": "circulation"},
        {"name": "Garage", "x": 3, "y": 10, "width": 4, "height": 3, "floor": "Main", "type": "utility"},
        {"name": "Basement", "x": 8.5, "y": 10, "width": 3, "height": 3, "floor": "Below", "type": "utility"},
        {"name": "Attic", "x": 6, "y": 1, "width": 3, "height": 2, "floor": "Above", "type": "utility"},
    ]
    for i in range(min(bedrooms, 5)):
        x = 9 + (i % 2) * 4
        y = 3.5 + (i // 2) * 3
        rooms.append({"name": f"Bedroom {i + 1}", "x": x, "y": y, "width": 3, "height": 2.5,
                      "floor": "Upper" if i < 2 else "Main", "type": "bedroom"})
    for i in range(min(int(bathrooms), 3)):
        rooms.append({"name": f"Bathroom {i + 1}", "x": 12, "y": 2.5 + i * 2, "width": 1.5, "height": 2,
                      "floor": "Main", "type": "bath"})
    return rooms


def _match_to_room(location_text, rooms, system):
    location_lower = (location_text or "").lower()
    room_keywords = {
        "kitchen": "Kitchen", "bathroom": "Bathroom 1", "master": "Bedroom 1",
        "bedroom": "Bedroom 2", "living": "Living Room", "garage": "Garage",
        "basement": "Basement", "attic": "Attic", "dining": "Dining Room",
        "hallway": "Hallway", "utility": "Garage", "laundry": "Bathroom 1",
    }
    for keyword, room_name in room_keywords.items():
        if keyword in location_lower:
            for room in rooms:
                if room_name.lower() in room.get("name", "").lower():
                    return room
    defaults = {"HVAC": "Garage", "ROOF": "Attic", "PLUMBING": "Kitchen",
                "ELECTRICAL": "Hallway", "STRUCTURAL": "Basement", "EXTERIOR": "Living Room"}
    default = defaults.get(system, "Living Room")
    for room in rooms:
        if default.lower() in room.get("name", "").lower():
            return room
    return rooms[0] if rooms else {"name": "Unknown", "x": 5, "y": 5, "width": 3, "height": 2, "floor": "Main"}


def _assign_wall(location_text):
    lower = (location_text or "").lower()
    for wall in ["north", "south", "east", "west", "front", "rear", "back"]:
        if wall in lower:
            return wall.title()
    return "Unknown"


def _assign_zone(system):
    zones = {"HVAC": "Mechanical", "ELECTRICAL": "Electrical", "PLUMBING": "Plumbing",
             "ROOF": "Structural", "STRUCTURAL": "Structural", "EXTERIOR": "Exterior",
             "FIRE_SAFETY": "Safety", "MOISTURE": "Environmental"}
    return zones.get(system, "General")


def _severity_color(severity):
    colors = {"CRITICAL": "#DC2626", "HIGH": "#EA580C", "MEDIUM": "#CA8A04",
              "LOW": "#16A34A", "INFO": "#2563EB"}
    return colors.get(severity, "#6B7280")


def _system_icon(system):
    icons = {"HVAC": "thermometer", "ROOF": "home", "ELECTRICAL": "bolt",
             "PLUMBING": "droplet", "STRUCTURAL": "building", "EXTERIOR": "tree",
             "INSULATION": "layers", "APPLIANCES": "appliance", "WINDOWS_DOORS": "window",
             "FIRE_SAFETY": "flame", "MOISTURE": "water"}
    return icons.get(system, "circle")