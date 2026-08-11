# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from google.cloud import firestore

# HARDCODED Project ID as required by Agent Platform rules
PROJECT_ID = "qwiklabs-gcp-03-3e728b1ac810"
COLLECTION_NAME = "anniversary_itineraries"


def seed_database():
    """Seeds the Firestore database with initial anniversary itinerary items."""
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection(COLLECTION_NAME)

    seeded_items = [
        {
            "itinerary_id": "itinerary_001",
            "title": "25th Silver Anniversary Maui Luxury Getaway",
            "milestone_years": 25,
            "destination": "Wailea, Maui, Hawaii",
            "total_cost": 4800.0,
            "max_budget": 5000.0,
            "duration_days": 5,
            "highlights": [
                "Private beachfront sunset dinner",
                "Complimentary silver-trimmed anniversary cake",
                "Private oceanfront cabana day",
            ],
            "notes": "Oceanfront views, gluten-free dining options preferred.",
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "itinerary_id": "itinerary_002",
            "title": "Amalfi Coast Cliffside Romantic Escape",
            "milestone_years": 25,
            "destination": "Positano, Italy",
            "total_cost": 5600.0,
            "max_budget": 6000.0,
            "duration_days": 6,
            "highlights": [
                "Private boat tour around Capri",
                "Michelin-star anniversary dinner",
                "Cliffside silver vow renewal setup",
            ],
            "notes": "Cliffside suite with panoramic sea views.",
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "itinerary_id": "itinerary_003",
            "title": "Paris & Loire Valley Chateau Romance",
            "milestone_years": 10,
            "destination": "Paris & Amboise, France",
            "total_cost": 5400.0,
            "max_budget": 6000.0,
            "duration_days": 6,
            "highlights": [
                "Private Seine River sunset dinner cruise",
                "Private wine tasting in historic chateau cellar",
            ],
            "notes": "Cultural escape with boutique hotel stays.",
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ]

    for item in seeded_items:
        doc_ref = collection.document(item["itinerary_id"])
        doc_ref.set(item)
        print(f"✅ Seeded document: {item['itinerary_id']} ({item['title']})")

    print("🎉 Firestore seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
