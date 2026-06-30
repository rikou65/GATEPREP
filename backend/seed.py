"""Seed data and seeding logic for GATEPREP."""
from __future__ import annotations

from shared import db, new_id, iso, now_utc, logger

SUBJECTS_SEED = [
    ("Engineering Mathematics", ["Linear Algebra", "Calculus", "Probability & Statistics"]),
    ("Discrete Mathematics", ["Sets & Relations", "Combinatorics", "Graph Theory",
                              "Propositional & Predicate Logic", "Group Theory"]),
    ("Digital Logic", ["Number Systems", "Boolean Algebra", "Combinational Circuits", "Sequential Circuits", "Minimization"]),
    ("Computer Organization and Architecture", ["Machine Instructions", "ALU & Datapath", "Pipelining", "Memory Hierarchy", "I/O Interface"]),
    ("C Programming", ["C Basics", "Pointers", "Functions & Recursion",
                       "Arrays & Strings", "Structures & Unions", "Dynamic Memory"]),
    ("Data Structures", ["Arrays", "Linked Lists", "Stacks & Queues", "Trees",
                         "Graphs", "Hashing", "Heaps"]),
    ("Algorithms", ["Asymptotic Analysis", "Searching & Sorting", "Greedy", "Divide & Conquer", "Dynamic Programming", "Graph Algorithms"]),
    ("Theory of Computation", ["Regular Languages", "Context-Free Languages", "Pushdown Automata", "Turing Machines", "Undecidability"]),
    ("Compiler Design", ["Lexical Analysis", "Parsing", "Syntax-Directed Translation", "Intermediate Code", "Code Optimization"]),
    ("Operating Systems", ["Processes & Threads", "CPU Scheduling", "Synchronization", "Deadlocks", "Memory Management", "File Systems"]),
    ("Databases", ["ER Model", "Relational Algebra", "SQL", "Normalization", "Transactions & Concurrency", "Indexing"]),
    ("Computer Networks", ["OSI & TCP/IP", "Physical Layer", "Data Link Layer", "Network Layer", "Transport Layer", "Application Layer"]),
]

SAMPLE_QUESTIONS = [
    {"subject": "Operating Systems", "topic": "CPU Scheduling", "qt": "MCQ",
     "qtext": "Which scheduling algorithm allocates CPU to the process with the smallest CPU burst time?",
     "opts": ["FCFS", "SJF", "Round Robin", "Priority"], "ans": "1",
     "sol": "Shortest Job First (SJF) selects the process with the smallest next CPU burst, minimizing average waiting time."},
    {"subject": "Operating Systems", "topic": "Synchronization", "qt": "MSQ",
     "qtext": "Which of the following are valid solutions to the critical section problem?",
     "opts": ["Peterson's algorithm", "Test-and-Set", "Disabling interrupts (uniprocessor)", "Busy waiting only"],
     "ans": ["0", "1", "2"],
     "sol": "Peterson's, TAS, and disabling interrupts on uniprocessors are valid; busy waiting alone is not sufficient."},
    {"subject": "Operating Systems", "topic": "Memory Management", "qt": "NAT",
     "qtext": "A system uses 32-bit addresses with 4 KB pages. How many bits are used for the page offset?",
     "opts": None, "ans": "12",
     "sol": "Page size = 4096 = 2^12, so offset = 12 bits."},
    {"subject": "Algorithms", "topic": "Asymptotic Analysis", "qt": "MCQ",
     "qtext": "What is the time complexity of binary search on a sorted array of n elements?",
     "opts": ["O(n)", "O(log n)", "O(n log n)", "O(1)"], "ans": "1",
     "sol": "Binary search halves the search space each iteration → O(log n)."},
    {"subject": "Algorithms", "topic": "Dynamic Programming", "qt": "MCQ",
     "qtext": "Which is NOT a property required for a problem to be solvable by DP?",
     "opts": ["Optimal substructure", "Overlapping subproblems", "Greedy choice", "Recursive formulation"],
     "ans": "2",
     "sol": "Greedy choice is required for greedy algorithms, not DP."},
    {"subject": "Databases", "topic": "Normalization", "qt": "MCQ",
     "qtext": "A relation in 3NF is automatically in:",
     "opts": ["1NF only", "2NF only", "1NF and 2NF", "BCNF"], "ans": "2",
     "sol": "3NF requires the relation to satisfy 1NF and 2NF first."},
    {"subject": "Databases", "topic": "SQL", "qt": "NAT",
     "qtext": "How many rows are returned by SELECT COUNT(*) FROM R where R has 100 rows and no WHERE clause?",
     "opts": None, "ans": "1",
     "sol": "COUNT(*) without GROUP BY returns a single row containing the count."},
    {"subject": "Computer Networks", "topic": "Transport Layer", "qt": "MCQ",
     "qtext": "Which protocol provides reliable, connection-oriented service?",
     "opts": ["UDP", "TCP", "IP", "ICMP"], "ans": "1",
     "sol": "TCP is connection-oriented and provides reliable delivery via acknowledgments."},
    {"subject": "Theory of Computation", "topic": "Regular Languages", "qt": "MCQ",
     "qtext": "Which of the following languages is NOT regular?",
     "opts": ["{a^n b^m | n,m ≥ 0}", "{a^n b^n | n ≥ 0}", "Strings ending in 'ab'", "Even-length strings over {a,b}"],
     "ans": "1",
     "sol": "{a^n b^n} requires counting and is not regular (provable by pumping lemma)."},
    {"subject": "Data Structures", "topic": "Trees", "qt": "NAT",
     "qtext": "What is the maximum number of nodes in a binary tree of height 3? (Root at height 0)",
     "opts": None, "ans": "15",
     "sol": "Maximum nodes in a binary tree of height h = 2^(h+1) - 1 = 2^4 - 1 = 15."},
    {"subject": "Digital Logic", "topic": "Boolean Algebra", "qt": "MCQ",
     "qtext": "A.(A+B) simplifies to:",
     "opts": ["A", "B", "A+B", "AB"], "ans": "0",
     "sol": "Absorption law: A.(A+B) = A."},
    {"subject": "Compiler Design", "topic": "Parsing", "qt": "MCQ",
     "qtext": "Which parser is most powerful?",
     "opts": ["LL(1)", "SLR", "LALR", "Canonical LR"], "ans": "3",
     "sol": "Canonical LR (CLR) handles the largest class of grammars among these."},
]

SAMPLE_PYQS = [
    {"subject": "Operating Systems", "topic": "Deadlocks", "year": 2023, "qt": "MCQ",
     "qtext": "Banker's algorithm is used for:",
     "opts": ["Deadlock prevention", "Deadlock avoidance", "Deadlock detection", "Deadlock recovery"],
     "ans": "1", "sol": "Banker's algorithm is a deadlock avoidance algorithm."},
    {"subject": "Algorithms", "topic": "Graph Algorithms", "year": 2022, "qt": "MCQ",
     "qtext": "Dijkstra's algorithm fails when the graph contains:",
     "opts": ["Cycles", "Negative weight edges", "Disconnected components", "Self loops"],
     "ans": "1", "sol": "Dijkstra assumes non-negative edge weights."},
    {"subject": "Databases", "topic": "Transactions & Concurrency", "year": 2021, "qt": "MCQ",
     "qtext": "Two-phase locking guarantees:",
     "opts": ["No deadlocks", "Serializability", "Recoverability", "Avoidance of starvation"],
     "ans": "1", "sol": "2PL ensures conflict-serializable schedules."},
    {"subject": "Computer Networks", "topic": "Network Layer", "year": 2023, "qt": "NAT",
     "qtext": "How many host bits in a /24 IPv4 network?",
     "opts": None, "ans": "8", "sol": "32 - 24 = 8 host bits."},
    {"subject": "Theory of Computation", "topic": "Turing Machines", "year": 2020, "qt": "MCQ",
     "qtext": "Which problem is undecidable?",
     "opts": ["Membership in regular language", "Emptiness of regular language",
              "Halting problem", "Equivalence of DFAs"],
     "ans": "2", "sol": "Halting problem is the classic undecidable problem (Turing 1936)."},
    {"subject": "Data Structures", "topic": "Hashing", "year": 2022, "qt": "MCQ",
     "qtext": "Open addressing with linear probing suffers most from:",
     "opts": ["Secondary clustering", "Primary clustering", "Chaining overhead", "Hash collisions only"],
     "ans": "1", "sol": "Linear probing causes primary clustering."},
]


async def _seed_subjects_and_topics() -> None:
    if await db.subjects.count_documents({}) > 0:
        return
    for i, (name, topics) in enumerate(SUBJECTS_SEED):
        sid = new_id("sub")
        await db.subjects.insert_one({
            "subject_id": sid, "name": name, "order": i,
            "created_at": iso(now_utc()),
        })
        topic_docs = [{
            "topic_id": new_id("top"), "subject_id": sid, "name": tname,
            "order": j, "created_at": iso(now_utc()),
        } for j, tname in enumerate(topics)]
        if topic_docs:
            await db.topics.insert_many(topic_docs)


async def _name_id_maps() -> tuple:
    """Build (subjects-by-name, topics-by-(subject_id,name)) maps."""
    subs = {s["name"]: s async for s in db.subjects.find({}, {"_id": 0})}
    tops = {(t["subject_id"], t["name"]): t
            async for t in db.topics.find({}, {"_id": 0})}
    return subs, tops


async def _seed_questions(subs: Dict[str, Any], tops: Dict[tuple, Any]) -> None:
    if await db.questions.count_documents({}) > 0:
        return
    for q in SAMPLE_QUESTIONS:
        s = subs.get(q["subject"])
        if not s:
            continue
        t = tops.get((s["subject_id"], q["topic"]))
        if not t:
            continue
        await db.questions.insert_one({
            "question_id": new_id("q"), "subject_id": s["subject_id"],
            "topic_id": t["topic_id"], "question_type": q["qt"],
            "question_text": q["qtext"], "options": q["opts"],
            "correct_answer": q["ans"], "solution": q["sol"],
            "source": "Seed Pack",
            "created_at": iso(now_utc()),
        })


async def _seed_pyqs(subs: Dict[str, Any], tops: Dict[tuple, Any]) -> None:
    if await db.pyqs.count_documents({}) > 0:
        return
    for p in SAMPLE_PYQS:
        s = subs.get(p["subject"])
        if not s:
            continue
        t = tops.get((s["subject_id"], p["topic"]))
        if not t:
            continue
        await db.pyqs.insert_one({
            "pyq_id": new_id("pyq"), "subject_id": s["subject_id"],
            "topic_id": t["topic_id"], "year": p["year"],
            "question_type": p["qt"], "question_text": p["qtext"],
            "options": p["opts"], "correct_answer": p["ans"],
            "solution": p["sol"],
            "source": f"GATE {p['year']}", "created_at": iso(now_utc()),
        })


async def seed_data() -> Dict[str, Any]:
    """Idempotent seed of subjects, topics, sample questions, sample PYQs."""
    await _seed_subjects_and_topics()
    subs, tops = await _name_id_maps()
    await _seed_questions(subs, tops)
    await _seed_pyqs(subs, tops)
    return {
        "subjects": await db.subjects.count_documents({}),
        "topics": await db.topics.count_documents({}),
        "questions": await db.questions.count_documents({}),
        "pyqs": await db.pyqs.count_documents({}),
    }


if __name__ == "__main__":
    import asyncio
    async def main():
        print("Seeding database...")
        res = await seed_data()
        print(f"Database seeded successfully: {res}")
    asyncio.run(main())
