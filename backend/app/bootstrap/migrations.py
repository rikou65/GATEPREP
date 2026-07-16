"""Database migrations for GATEPREP."""
from __future__ import annotations

from typing import Dict, List

from app.core.ids import new_id
from app.core.logging import logger
from app.core.time import iso, now_utc

db = None


def configure(database) -> None:
    global db
    db = database

# Official GATE CS 2026 syllabus topics (per Subject).
# Engineering Mathematics is intentionally kept as-is in current DB; Discrete
# Mathematics remains a separate subject. Topics below match the official PDF.
OFFICIAL_SYLLABUS_V3: Dict[str, List[str]] = {
    "Discrete Mathematics": [
        "Propositional and First Order Logic",
        "Sets, Relations, Functions, Partial Orders & Lattices",
        "Monoids & Groups",
        "Graphs: Connectivity, Matching, Colouring",
        "Combinatorics: Counting, Recurrence Relations, Generating Functions",
    ],
    "Digital Logic": [
        "Boolean Algebra",
        "Combinational Circuits",
        "Sequential Circuits",
        "Minimization",
        "Number Representations & Computer Arithmetic",
    ],
    "Computer Organization and Architecture": [
        "Machine Instructions & Addressing Modes",
        "ALU, Data-path & Control Unit",
        "Instruction Pipelining & Pipeline Hazards",
        "Memory Hierarchy: Cache, Main, Secondary",
        "I/O Interface (Interrupt & DMA)",
    ],
    "C Programming": [
        "Programming in C",
        "Recursion",
        "Pointers",
        "Arrays & Strings",
        "Structures & Unions",
        "Dynamic Memory",
    ],
    "Data Structures": [
        "Arrays",
        "Stacks",
        "Queues",
        "Linked Lists",
        "Trees",
        "Binary Search Trees",
        "Binary Heaps",
        "Graphs",
    ],
    "Algorithms": [
        "Asymptotic Complexity (Time & Space)",
        "Searching",
        "Sorting",
        "Hashing",
        "Greedy",
        "Dynamic Programming",
        "Divide & Conquer",
        "Graph Traversals",
        "Minimum Spanning Trees",
        "Shortest Paths",
    ],
    "Theory of Computation": [
        "Regular Expressions & Finite Automata",
        "Context-Free Grammars & Push-Down Automata",
        "Regular & Context-Free Languages, Pumping Lemma",
        "Turing Machines & Undecidability",
    ],
    "Compiler Design": [
        "Lexical Analysis",
        "Parsing",
        "Syntax-Directed Translation",
        "Runtime Environments",
        "Intermediate Code Generation",
        "Local Optimization",
        "Data Flow Analyses (Constant Propagation, Liveness, Common Sub-expression)",
    ],
    "Operating Systems": [
        "System Calls",
        "Processes, Threads & IPC",
        "Concurrency & Synchronization",
        "Deadlock",
        "CPU & I/O Scheduling",
        "Memory Management & Virtual Memory",
        "File Systems",
    ],
    "Databases": [
        "ER Model",
        "Relational Algebra, Tuple Calculus, SQL",
        "Integrity Constraints & Normal Forms",
        "File Organization & Indexing (B / B+ Trees)",
        "Transactions & Concurrency Control",
    ],
    "Computer Networks": [
        "Layering: OSI & TCP/IP",
        "Packet, Circuit & Virtual-Circuit Switching",
        "Data Link Layer: Framing, Error Detection, MAC, Ethernet Bridging",
        "Routing Protocols: Shortest Path, Flooding, Distance Vector, Link State",
        "IP Addressing, IPv4, CIDR, Fragmentation",
        "IP Support Protocols (ARP, DHCP, ICMP, NAT)",
        "Transport Layer: Flow & Congestion Control, UDP, TCP, Sockets",
        "Application Layer: DNS, SMTP, HTTP, FTP, Email",
    ],
}

# Legacy topic name → official topic name. Used to merge old seed topics into
# the official ones, moving all attached questions/PYQs/notes/mistakes over.
LEGACY_TOPIC_REMAP: Dict[str, Dict[str, str]] = {
    "Discrete Mathematics": {
        "Sets & Relations": "Sets, Relations, Functions, Partial Orders & Lattices",
        "Combinatorics": "Combinatorics: Counting, Recurrence Relations, Generating Functions",
        "Graph Theory": "Graphs: Connectivity, Matching, Colouring",
        "Propositional & Predicate Logic": "Propositional and First Order Logic",
        "Group Theory": "Monoids & Groups",
    },
    "Digital Logic": {
        "Number Systems": "Number Representations & Computer Arithmetic",
    },
    "Computer Organization and Architecture": {
        "Machine Instructions": "Machine Instructions & Addressing Modes",
        "ALU & Datapath": "ALU, Data-path & Control Unit",
        "Pipelining": "Instruction Pipelining & Pipeline Hazards",
        "Memory Hierarchy": "Memory Hierarchy: Cache, Main, Secondary",
        "I/O Interface": "I/O Interface (Interrupt & DMA)",
    },
    "C Programming": {
        "C Basics": "Programming in C",
        "Functions & Recursion": "Recursion",
    },
    "Data Structures": {
        "Heaps": "Binary Heaps",
        "Stacks & Queues": "Stacks",
    },
    "Algorithms": {
        "Asymptotic Analysis": "Asymptotic Complexity (Time & Space)",
        "Searching & Sorting": "Searching",
        "Graph Algorithms": "Graph Traversals",
    },
    "Theory of Computation": {
        "Regular Languages": "Regular Expressions & Finite Automata",
        "Context-Free Languages": "Context-Free Grammars & Push-Down Automata",
        "Pushdown Automata": "Context-Free Grammars & Push-Down Automata",
        "Turing Machines": "Turing Machines & Undecidability",
        "Undecidability": "Turing Machines & Undecidability",
    },
    "Compiler Design": {
        "Syntax-Directed Translation": "Syntax-Directed Translation",
        "Intermediate Code": "Intermediate Code Generation",
        "Code Optimization": "Local Optimization",
    },
    "Operating Systems": {
        "Processes & Threads": "Processes, Threads & IPC",
        "CPU Scheduling": "CPU & I/O Scheduling",
        "Synchronization": "Concurrency & Synchronization",
        "Deadlocks": "Deadlock",
        "Memory Management": "Memory Management & Virtual Memory",
    },
    "Databases": {
        "Relational Algebra": "Relational Algebra, Tuple Calculus, SQL",
        "SQL": "Relational Algebra, Tuple Calculus, SQL",
        "Normalization": "Integrity Constraints & Normal Forms",
        "Transactions & Concurrency": "Transactions & Concurrency Control",
        "Indexing": "File Organization & Indexing (B / B+ Trees)",
    },
    "Computer Networks": {
        "OSI & TCP/IP": "Layering: OSI & TCP/IP",
        "Physical Layer": "Packet, Circuit & Virtual-Circuit Switching",
        "Data Link Layer": "Data Link Layer: Framing, Error Detection, MAC, Ethernet Bridging",
        "Network Layer": "IP Addressing, IPv4, CIDR, Fragmentation",
        "Transport Layer": "Transport Layer: Flow & Congestion Control, UDP, TCP, Sockets",
        "Application Layer": "Application Layer: DNS, SMTP, HTTP, FTP, Email",
    },
}

# Cross-subject moves: e.g., Hashing moves from Data Structures (legacy) to
# Algorithms (official syllabus). Format: legacy_topic_name → (target_subject_name, target_topic_name)
CROSS_SUBJECT_MOVES: Dict[str, tuple] = {
    "Hashing": ("Algorithms", "Hashing"),
}


async def _migrate_per_user_content() -> None:
    """One-time migration: stamp any question / pyq without a user_id to the
    first user in the system (so seed data stays usable in single-user dev mode).
    On a fresh container with no users yet, this is a no-op."""
    first_user = await db.users.find_one({}, {"_id": 0, "user_id": 1}, sort=[("created_at", 1)])
    if not first_user:
        return
    uid = first_user["user_id"]
    r1 = await db.questions.update_many({"user_id": {"$exists": False}}, {"$set": {"user_id": uid}})
    r2 = await db.pyqs.update_many({"user_id": {"$exists": False}}, {"$set": {"user_id": uid}})
    if r1.modified_count or r2.modified_count:
        logger.info(f"Stamped {r1.modified_count} questions and {r2.modified_count} pyqs to first user {uid}")


async def _purge_global_staging_records() -> None:
    """Remove staging/import records that lack a user_id (global records pre-dating tenant isolation)."""
    r1 = await db.staging_questions.delete_many({"user_id": {"$exists": False}})
    r2 = await db.import_jobs.delete_many({"user_id": {"$exists": False}})
    if r1.deleted_count or r2.deleted_count:
        logger.info(f"Purged {r1.deleted_count} staging items and {r2.deleted_count} import jobs without user_id")


async def _hash_existing_session_tokens() -> None:
    """One-time migration: hash any plaintext session tokens at rest.

    HMAC-SHA256 hex digests are 64 hex chars. ``secrets.token_urlsafe`` tokens
    contain ``-_`` and are ~43 chars, so a stored value that is NOT 64 hex
    chars must be a legacy plaintext token that needs hashing.

    Also collapses any duplicate rows sharing the same stored token value
    (keeping the newest by ``_id``) so the upcoming unique index on
    ``session_token`` can be created — random tokens never collide in
    production, but stale test/dev data may.
    """
    from app.core.security import hash_session_token

    hex_chars = set("0123456789abcdef")

    # Dedupe first: group by the stored token value and delete all but the
    # newest row in each duplicate group.
    async for grp in db.user_sessions.aggregate([
        {"$group": {
            "_id": "$session_token",
            "ids": {"$push": "$_id"},
            "count": {"$sum": 1},
        }},
        {"$match": {"count": {"$gt": 1}}},
    ]):
        ids = sorted(grp["ids"], reverse=True)  # newest _id first
        await db.user_sessions.delete_many({"_id": {"$in": ids[1:]}})

    migrated = 0
    skipped = 0
    async for doc in db.user_sessions.find({}, {"_id": 1, "session_token": 1}):
        tok = doc.get("session_token")
        if not tok:
            continue
        if len(tok) == 64 and all(c in hex_chars for c in tok.lower()):
            continue
        try:
            await db.user_sessions.update_one(
                {"_id": doc["_id"]},
                {"$set": {"session_token": hash_session_token(tok)}},
            )
            migrated += 1
        except Exception:
            # A residual collision (e.g. two rows that dedupe missed) — drop
            # the loser rather than let startup crash on a stale dev session.
            await db.user_sessions.delete_one({"_id": doc["_id"]})
            skipped += 1
    if migrated:
        logger.info(f"Hashed {migrated} plaintext session tokens at rest")
    if skipped:
        logger.warning(f"Skipped {skipped} duplicate session rows during hashing")


async def _encrypt_existing_token_credentials() -> None:
    """One-time migration: encrypt any plaintext OAuth tokens at rest.

    Skips entirely when ``TOKEN_ENCRYPTION_KEY`` is not configured. When
    enabled, values that fail Fernet decryption (legacy plaintext) are
    re-encrypted; already-encrypted values are left untouched.
    """
    from app.core.crypto import decrypt_secret, encrypt_secret, is_encryption_enabled

    if not is_encryption_enabled():
        return

    token_fields = ("access_token", "refresh_token")
    migrated = 0
    for coll_name in ("drive_credentials", "youtube_credentials"):
        coll = db[coll_name]
        async for doc in coll.find({}, {"_id": 1, **{f: 1 for f in token_fields}}):
            updates = {}
            for f in token_fields:
                v = doc.get(f)
                if not v:
                    continue
                decrypted = decrypt_secret(v)
                if decrypted == v:
                    updates[f] = encrypt_secret(v)
            if updates:
                await coll.update_one({"_id": doc["_id"]}, {"$set": updates})
                migrated += 1
    if migrated:
        logger.info(f"Encrypted {migrated} plaintext OAuth token documents at rest")


async def _ensure_runtime_indexes() -> None:
    try:
        await db.question_flags.create_index(
            [("user_id", 1), ("question_id", 1), ("flag_type", 1)], unique=True
        )
        await db.pyq_flags.create_index(
            [("user_id", 1), ("pyq_id", 1), ("flag_type", 1)], unique=True
        )
        # Phase 7 performance indexes for user-owned study data.
        await db.questions.create_index([("user_id", 1), ("subject_id", 1)])
        await db.questions.create_index([("user_id", 1), ("subject_id", 1), ("topic_id", 1)])
        await db.pyqs.create_index([("user_id", 1), ("subject_id", 1)])
        await db.pyqs.create_index([("user_id", 1), ("subject_id", 1), ("topic_id", 1)])
        await db.question_attempts.create_index([("user_id", 1), ("question_id", 1)])
        await db.pyq_attempts.create_index([("user_id", 1), ("pyq_id", 1)])
        await db.staging_questions.create_index([("user_id", 1), ("status", 1)])
        await db.import_jobs.create_index([("user_id", 1), ("status", 1)])
        await db.resources.create_index([("user_id", 1), ("subject_id", 1)])
        await db.resources.create_index([("user_id", 1), ("subject_id", 1), ("resource_type", 1)])
        await db.playlists.create_index([("user_id", 1), ("subject_id", 1)])
        await db.videos.create_index([("playlist_id", 1), ("position", 1)])
        await db.video_progress.create_index([("user_id", 1), ("video_id", 1)], unique=True)
        await db.video_progress.create_index([("user_id", 1), ("last_watched_at", -1)])
        await db.video_notes.create_index([("user_id", 1), ("video_id", 1)], unique=True)
        await db.mistakes.create_index([("user_id", 1), ("subject_id", 1)])

        # Auth + token hot-path indexes (every authenticated request).
        # email / supabase_user_id are intentionally non-unique: legacy data
        # may contain duplicates that IdentityRepairService is designed to
        # merge; enforcing uniqueness here would reject those merges.
        await db.users.create_index("email", sparse=True)
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("supabase_user_id", sparse=True)
        await db.user_sessions.create_index("session_token", unique=True)
        await db.oauth_states.create_index("state")
        await db.oauth_states.create_index(
            [("purpose", 1), ("used", 1), ("expires_at", 1)]
        )
        await db.drive_credentials.create_index("user_id", unique=True)
        await db.youtube_credentials.create_index("user_id", unique=True)

        # Resource/question notes hot paths (per-item reads/writes).
        await db.question_notes.create_index(
            [("user_id", 1), ("question_id", 1)]
        )
        await db.resource_notes.create_index(
            [("resource_id", 1), ("user_id", 1)], unique=True
        )
    except Exception as e:
        logger.warning(f"index creation: {e}")


async def _migrate_v2_split_subjects() -> None:
    """Idempotent migration: split Discrete Math out of Engineering Math, and
    split Programming and Data Structures into C Programming + Data Structures.
    Then align topics to the official GATE CS 2026 syllabus."""
    await _split_discrete_math_out()
    await _split_pad_into_cp_and_ds()
    await _reorder_subjects()
    await _align_topics_to_official_syllabus()
    await _merge_legacy_topics()
    await _delete_empty_legacy_topics()


async def _split_discrete_math_out() -> None:
    if await db.subjects.find_one({"name": "Discrete Mathematics"}, {"_id": 0}):
        return
    new_sid = new_id("sub")
    await db.subjects.insert_one({
        "subject_id": new_sid, "name": "Discrete Mathematics", "order": 1,
        "created_at": iso(now_utc()),
    })
    topics = ["Sets & Relations", "Combinatorics", "Graph Theory",
              "Propositional & Predicate Logic", "Group Theory"]
    new_topic_ids: List[str] = []
    for j, t in enumerate(topics):
        tid = new_id("top")
        await db.topics.insert_one({
            "topic_id": tid, "subject_id": new_sid, "name": t,
            "order": j, "created_at": iso(now_utc()),
        })
        new_topic_ids.append(tid)
    em = await db.subjects.find_one({"name": "Engineering Mathematics"}, {"_id": 0})
    if not em:
        return
    old_topic = await db.topics.find_one(
        {"subject_id": em["subject_id"], "name": "Discrete Mathematics"}, {"_id": 0}
    )
    if not old_topic:
        return
    target_tid = new_topic_ids[0]
    set_fields = {"subject_id": new_sid, "topic_id": target_tid}
    await db.questions.update_many({"topic_id": old_topic["topic_id"]}, {"$set": set_fields})
    await db.pyqs.update_many({"topic_id": old_topic["topic_id"]}, {"$set": set_fields})
    await db.mistakes.update_many({"topic_id": old_topic["topic_id"]}, {"$set": set_fields})
    await db.topics.delete_one({"topic_id": old_topic["topic_id"]})
    logger.info("Migrated: Discrete Mathematics split into own subject")


async def _split_pad_into_cp_and_ds() -> None:
    old_pad = await db.subjects.find_one(
        {"name": "Programming and Data Structures"}, {"_id": 0}
    )
    if not old_pad:
        return
    cp_sid = new_id("sub")
    ds_sid = new_id("sub")
    await db.subjects.insert_one({
        "subject_id": cp_sid, "name": "C Programming", "order": 4,
        "created_at": iso(now_utc()),
    })
    await db.subjects.insert_one({
        "subject_id": ds_sid, "name": "Data Structures", "order": 5,
        "created_at": iso(now_utc()),
    })
    cp_topics = ["C Basics", "Pointers", "Functions & Recursion",
                 "Arrays & Strings", "Structures & Unions", "Dynamic Memory"]
    ds_topics = ["Arrays", "Linked Lists", "Stacks & Queues", "Trees",
                 "Graphs", "Hashing", "Heaps"]
    cp_map: Dict[str, str] = {}
    ds_map: Dict[str, str] = {}
    for j, t in enumerate(cp_topics):
        tid = new_id("top")
        await db.topics.insert_one({
            "topic_id": tid, "subject_id": cp_sid, "name": t,
            "order": j, "created_at": iso(now_utc()),
        })
        cp_map[t] = tid
    for j, t in enumerate(ds_topics):
        tid = new_id("top")
        await db.topics.insert_one({
            "topic_id": tid, "subject_id": ds_sid, "name": t,
            "order": j, "created_at": iso(now_utc()),
        })
        ds_map[t] = tid
    routing: Dict[str, tuple] = {
        "C Programming": (cp_sid, cp_map["C Basics"]),
        "Arrays & Strings": (ds_sid, ds_map["Arrays"]),
        "Linked Lists": (ds_sid, ds_map["Linked Lists"]),
        "Stacks & Queues": (ds_sid, ds_map["Stacks & Queues"]),
        "Trees": (ds_sid, ds_map["Trees"]),
        "Graphs": (ds_sid, ds_map["Graphs"]),
        "Hashing": (ds_sid, ds_map["Hashing"]),
    }
    old_topics = await db.topics.find(
        {"subject_id": old_pad["subject_id"]}, {"_id": 0}
    ).to_list(200)
    for ot in old_topics:
        target = routing.get(ot["name"])
        if target:
            new_sid, new_tid = target
            set_fields = {"subject_id": new_sid, "topic_id": new_tid}
            await db.questions.update_many({"topic_id": ot["topic_id"]}, {"$set": set_fields})
            await db.pyqs.update_many({"topic_id": ot["topic_id"]}, {"$set": set_fields})
            await db.mistakes.update_many({"topic_id": ot["topic_id"]}, {"$set": set_fields})
        await db.topics.delete_one({"topic_id": ot["topic_id"]})
    await db.subjects.delete_one({"subject_id": old_pad["subject_id"]})
    await db.resources.update_many(
        {"subject_id": old_pad["subject_id"]}, {"$set": {"subject_id": ds_sid}}
    )
    await db.playlists.update_many(
        {"subject_id": old_pad["subject_id"]}, {"$set": {"subject_id": ds_sid}}
    )
    logger.info("Migrated: PaD split into C Programming + Data Structures")


async def _reorder_subjects() -> None:
    desired = [
        "Engineering Mathematics", "Discrete Mathematics", "Digital Logic",
        "Computer Organization and Architecture", "C Programming", "Data Structures",
        "Algorithms", "Theory of Computation", "Compiler Design",
        "Operating Systems", "Databases", "Computer Networks",
    ]
    for i, name in enumerate(desired):
        await db.subjects.update_one({"name": name}, {"$set": {"order": i}})


async def _align_topics_to_official_syllabus() -> None:
    """Idempotent upsert: ensure each subject has the official topic list."""
    for subject_name, topics in OFFICIAL_SYLLABUS_V3.items():
        subj = await db.subjects.find_one({"name": subject_name}, {"_id": 0})
        if not subj:
            continue
        sid = subj["subject_id"]
        for j, t_name in enumerate(topics):
            existing = await db.topics.find_one(
                {"subject_id": sid, "name": t_name}, {"_id": 0}
            )
            if existing:
                await db.topics.update_one(
                    {"topic_id": existing["topic_id"]}, {"$set": {"order": j}}
                )
            else:
                await db.topics.insert_one({
                    "topic_id": new_id("top"), "subject_id": sid,
                    "name": t_name, "order": j, "created_at": iso(now_utc()),
                })
        legacy = await db.topics.find(
            {"subject_id": sid, "name": {"$nin": topics}}, {"_id": 0}
        ).to_list(500)
        for k, lt in enumerate(legacy):
            await db.topics.update_one(
                {"topic_id": lt["topic_id"]},
                {"$set": {"order": len(topics) + k}},
            )


async def _merge_legacy_topics() -> None:
    """For each subject, merge legacy topics into their official equivalents."""
    for subject_name, remap in LEGACY_TOPIC_REMAP.items():
        subj = await db.subjects.find_one({"name": subject_name}, {"_id": 0})
        if not subj:
            continue
        sid = subj["subject_id"]
        for old_name, new_name in remap.items():
            old = await db.topics.find_one({"subject_id": sid, "name": old_name}, {"_id": 0})
            if not old:
                continue
            new = await db.topics.find_one({"subject_id": sid, "name": new_name}, {"_id": 0})
            if not new:
                continue
            set_fields = {"subject_id": sid, "topic_id": new["topic_id"]}
            await db.questions.update_many({"topic_id": old["topic_id"]}, {"$set": set_fields})
            await db.pyqs.update_many({"topic_id": old["topic_id"]}, {"$set": set_fields})
            await db.mistakes.update_many({"topic_id": old["topic_id"]}, {"$set": set_fields})
            await db.topics.delete_one({"topic_id": old["topic_id"]})

    for old_name, (tgt_subject, tgt_topic) in CROSS_SUBJECT_MOVES.items():
        target_subj = await db.subjects.find_one({"name": tgt_subject}, {"_id": 0})
        if not target_subj:
            continue
        target = await db.topics.find_one(
            {"subject_id": target_subj["subject_id"], "name": tgt_topic}, {"_id": 0}
        )
        if not target:
            continue
        legacy_topics = await db.topics.find(
            {"name": old_name, "subject_id": {"$ne": target_subj["subject_id"]}}, {"_id": 0}
        ).to_list(50)
        for lt in legacy_topics:
            set_fields = {"subject_id": target_subj["subject_id"], "topic_id": target["topic_id"]}
            await db.questions.update_many({"topic_id": lt["topic_id"]}, {"$set": set_fields})
            await db.pyqs.update_many({"topic_id": lt["topic_id"]}, {"$set": set_fields})
            await db.mistakes.update_many({"topic_id": lt["topic_id"]}, {"$set": set_fields})
            await db.topics.delete_one({"topic_id": lt["topic_id"]})


async def _delete_empty_legacy_topics() -> None:
    """Remove any topic that is NOT in the official syllabus list AND has no content."""
    for subject_name, official_topics in OFFICIAL_SYLLABUS_V3.items():
        subj = await db.subjects.find_one({"name": subject_name}, {"_id": 0})
        if not subj:
            continue
        extras = await db.topics.find(
            {"subject_id": subj["subject_id"], "name": {"$nin": official_topics}}, {"_id": 0}
        ).to_list(500)
        for t in extras:
            tid = t["topic_id"]
            refs = (
                await db.questions.count_documents({"topic_id": tid})
                + await db.pyqs.count_documents({"topic_id": tid})
                + await db.mistakes.count_documents({"topic_id": tid})
            )
            if refs == 0:
                await db.topics.delete_one({"topic_id": tid})
