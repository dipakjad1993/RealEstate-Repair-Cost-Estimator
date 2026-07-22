import random
from datetime import datetime

def create_spatial_map(findings, property_data):
    rooms = _generate_floor_plan(property_data)
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
            "room": room["name"],
            "wall": _assign_wall(location_text),
            "floor_level": room.get("floor", "Main"),
            "x_position": room.get("x", 0) + random.uniform(-0.5, 0.5),
            "y_position": room.get("y", 0) + random.uniform(-0.5, 0.5),
            "zone": zone,
            "color": _severity_color(finding.get("severity", "MEDIUM")),
            "icon": _system_icon(system),
        })
    return {
        "floor_plan": rooms,
        "findings_mapped": spatial_items,
        "total_mapped": len(spatial_items),
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

def _generate_floor_plan(property_data):
    bedrooms = property_data.get("bedrooms", 3)
    bathrooms = property_data.get("bathrooms", 2)
    rooms = [
        {"name": "Living Room", "x": 2, "y": 2, "width": 4, "height": 3, "floor": "Main", "type": "common"},
        {"name": "Kitchen", "x": 7, "y": 2, "width": 3, "height": 3, "floor": "Main", "type": "common"},
        {"name": "Dining Room", "x": 2, "y": 6, "width": 3, "height": 2, "floor": "Main", "type": "common"},
        {"name": "Hallway", "x": 6, "y": 6, "width": 4, "height": 1, "floor": "Main", "type": "circulation"},
        {"name": "Garage", "x": 2, "y": 9, "width": 4, "height": 3, "floor": "Main", "type": "utility"},
        {"name": "Basement", "x": 7, "y": 9, "width": 3, "height": 3, "floor": "Below", "type": "utility"},
        {"name": "Attic", "x": 5, "y": 0, "width": 3, "height": 2, "floor": "Above", "type": "utility"},
    ]
    for i in range(min(bedrooms, 5)):
        x = 7 + (i % 2) * 4
        y = 3 + (i // 2) * 3
        rooms.append({"name": f"Bedroom {i + 1}", "x": x, "y": y, "width": 3, "height": 2.5, "floor": "Upper" if i < 2 else "Main", "type": "bedroom"})
    for i in range(min(int(bathrooms), 3)):
        rooms.append({"name": f"Bathroom {i + 1}", "x": 11, "y": 2 + i * 2, "width": 1.5, "height": 2, "floor": "Main", "type": "bath"})
    return rooms

def _match_to_room(location_text, rooms, system):
    location_lower = location_text.lower()
    room_keywords = {
        "kitchen": "Kitchen", "bathroom": "Bathroom 1", "master": "Bedroom 1",
        "bedroom": "Bedroom 2", "living": "Living Room", "garage": "Garage",
        "basement": "Basement", "attic": "Attic", "dining": "Dining Room",
        "hallway": "Hallway", "utility": "Garage",
    }
    system_room_defaults = {
        "HVAC": "Garage", "ROOF": "Attic", "PLUMBING": "Kitchen",
        "ELECTRICAL": "Hallway", "STRUCTURAL": "Basement", "EXTERIOR": "Living Room",
    }
    for keyword, room_name in room_keywords.items():
        if keyword in location_lower:
            for room in rooms:
                if room_name.lower() in room["name"].lower():
                    return room
    default = system_room_defaults.get(system, "Living Room")
    for room in rooms:
        if default.lower() in room["name"].lower():
            return room
    return rooms[0] if rooms else {"name": "Unknown", "x": 5, "y": 5}

def _assign_wall(location_text):
    location_lower = location_text.lower()
    for wall in ["north", "south", "east", "west", "front", "rear", "back"]:
        if wall in location_lower:
            return wall.title()
    return "Unknown"

def _assign_zone(system):
    zones = {
        "HVAC": "Mechanical", "ELECTRICAL": "Electrical", "PLUMBING": "Plumbing",
        "ROOF": "Structural", "STRUCTURAL": "Structural", "EXTERIOR": "Exterior",
        "FIRE_SAFETY": "Safety", "MOISTURE": "Environmental",
    }
    return zones.get(system, "General")

def _severity_color(severity):
    colors = {"CRITICAL": "#DC2626", "HIGH": "#EA580C", "MEDIUM": "#CA8A04", "LOW": "#16A34A", "INFO": "#2563EB"}
    return colors.get(severity, "#6B7280")

def _system_icon(system):
    icons = {
        "HVAC": "thermometer", "ROOF": "home", "ELECTRICAL": "bolt",
        "PLUMBING": "droplet", "STRUCTURAL": "building", "EXTERIOR": "tree",
        "INSULATION": "layers", "APPLIANCES": "appliance", "WINDOWS_DOORS": "window",
        "FIRE_SAFETY": "flame", "MOISTURE": "water",
    }
    return icons.get(system, "circle")
