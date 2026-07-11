import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  RadialBarChart, RadialBar, PieChart, Pie, Cell,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
} from "recharts";
import {
  Target, BookCheck, History, TrendingUp, AlertOctagon,
  ArrowUpRight, ChevronDown, ChevronUp, BarChart3
} from "lucide-react";
import Layout from "@/components/Layout";
import { useDashboard, useSubjectAnalyticsLoader } from "@/features/dashboard/hooks/useDashboard";

/* ─── colour palette ─── */
const EMERALD  = "#10B981";
const BLUE     = "#3B82F6";
const AMBER    = "#F59E0B";
const VIOLET   = "#A78BFA";
const ROSE     = "#F43F5E";
const CYAN     = "#06B6D4";
const PIE_COLORS = [EMERALD, BLUE, AMBER, VIOLET, ROSE, CYAN, "#818CF8", "#FB923C", "#34D399", "#E879F9"];

const tooltipStyle = {
  background: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  fontSize: 12,
  borderRadius: 8,
};
const axisStroke = "hsl(var(--muted-foreground))";

/* ─── helper: accuracy colour ─── */
const accTone = (acc, has) => {
  if (!has) return "text-muted-foreground/50";
  if (acc >= 75) return "text-emerald-400";
  if (acc >= 50) return "text-amber-400";
  return "text-red-400";
};
const accBg = (acc, has) => {
  if (!has) return "bg-muted-foreground/20";
  if (acc >= 75) return "bg-emerald-500";
  if (acc >= 50) return "bg-amber-500";
  return "bg-red-500";
};

/* ─── small stat card ─── */
const Stat = ({ icon: Icon, label, value, suffix, sub }) => (
  <div className="border border-border rounded-lg p-4 bg-card/40">
    <div className="flex items-start justify-between mb-2">
      <Icon className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
    </div>
    <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">{label}</div>
    <div className="flex items-baseline gap-1 mt-1">
      <span className="text-2xl font-bold mono">{value}</span>
      {suffix && <span className="text-sm text-muted-foreground mono">{suffix}</span>}
    </div>
    {sub && <div className="text-[10px] text-muted-foreground mt-0.5 mono">{sub}</div>}
  </div>
);

/* ─── overall accuracy radial ─── */
const AccuracyGauge = ({ label, value, fill }) => {
  const chartData = [{ name: label, value, fill }];
  return (
    <div className="flex flex-col items-center">
      <RadialBarChart
        width={120} height={120} cx={60} cy={60}
        innerRadius={40} outerRadius={55} barSize={10}
        data={chartData} startAngle={210} endAngle={-30}
      >
        <RadialBar dataKey="value" cornerRadius={5} background={{ fill: "hsl(var(--border))" }} />
      </RadialBarChart>
      <div className="text-center -mt-4">
        <div className="text-xl font-bold mono">{value}%</div>
        <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">{label}</div>
      </div>
    </div>
  );
};

/* ─── per-subject expandable card ─── */
const SubjectAnalyticsCard = ({ row, topicData, onToggle, open }) => {
  const { subject, qb, pyq } = row;
  const totalSolved = qb.solved + pyq.solved;
  const totalItems = qb.total + pyq.total;
  const overallAcc = totalSolved > 0
    ? Math.round(((qb.solved > 0 ? qb.accuracy * qb.solved : 0) + (pyq.solved > 0 ? pyq.accuracy * pyq.solved : 0)) / totalSolved * 10) / 10
    : 0;
  const qbPct = qb.total > 0 ? Math.round((qb.solved / qb.total) * 100) : 0;
  const pyqPct = pyq.total > 0 ? Math.round((pyq.solved / pyq.total) * 100) : 0;

  const topicChartData = (topicData || []).map(t => ({
    name: t.topic.name.length > 18 ? t.topic.name.slice(0, 16) + "…" : t.topic.name,
    fullName: t.topic.name,
    "QBank Solved": t.qb.solved,
    "PYQ Solved": t.pyq.solved,
    "QBank Acc": t.qb.accuracy,
    "PYQ Acc": t.pyq.accuracy,
  }));

  return (
    <section className="border border-border rounded-xl overflow-hidden bg-card/20" data-testid={`analytics-subject-${subject.subject_id}`}>
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-5 hover:bg-secondary/20 transition-colors text-left"
      >
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center text-sm font-bold mono text-muted-foreground">
            {String(subject.order + 1).padStart(2, "0")}
          </div>
          <div>
            <h3 className="text-base font-semibold">{subject.name}</h3>
            <div className="text-xs text-muted-foreground mt-0.5 mono">
              {totalSolved}/{totalItems} solved · <span className={accTone(overallAcc, totalSolved > 0)}>{overallAcc}% accuracy</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* mini progress bars */}
          <div className="hidden sm:flex items-center gap-3">
            <MiniBar label="QB" pct={qbPct} acc={qb.accuracy} solved={qb.solved} />
            <MiniBar label="PYQ" pct={pyqPct} acc={pyq.accuracy} solved={pyq.solved} />
          </div>
          {open ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
        </div>
      </button>

      {/* Expanded Content */}
      {open && (
        <div className="border-t border-border">
          {/* Stats Row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-5">
            <MiniStat label="QBank Solved" value={`${qb.solved}/${qb.total}`} sub={`${qb.remaining} remaining`} />
            <MiniStat label="QBank Accuracy" value={`${qb.accuracy}%`} tone={accTone(qb.accuracy, qb.solved > 0)} />
            <MiniStat label="PYQ Solved" value={`${pyq.solved}/${pyq.total}`} sub={`${pyq.remaining} remaining`} />
            <MiniStat label="PYQ Accuracy" value={`${pyq.accuracy}%`} tone={accTone(pyq.accuracy, pyq.solved > 0)} />
          </div>

          {/* Topic Breakdown Chart */}
          {topicChartData.length > 0 && (
            <div className="px-5 pb-5 space-y-5">
              <div className="border border-border rounded-lg p-4">
                <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">Questions solved · by topic</div>
                <ResponsiveContainer width="100%" height={Math.max(200, topicChartData.length * 32)}>
                  <BarChart data={topicChartData} layout="vertical" margin={{ left: 10, right: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                    <XAxis type="number" stroke={axisStroke} fontSize={10} />
                    <YAxis dataKey="name" type="category" stroke={axisStroke} fontSize={10} width={120} tick={{ fill: axisStroke }} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(val, name, props) => [val, name]} labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="QBank Solved" fill={EMERALD} radius={[0, 3, 3, 0]} />
                    <Bar dataKey="PYQ Solved" fill={BLUE} radius={[0, 3, 3, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="border border-border rounded-lg p-4">
                <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">Accuracy · by topic</div>
                <ResponsiveContainer width="100%" height={Math.max(200, topicChartData.length * 32)}>
                  <BarChart data={topicChartData} layout="vertical" margin={{ left: 10, right: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                    <XAxis type="number" stroke={axisStroke} fontSize={10} domain={[0, 100]} unit="%" />
                    <YAxis dataKey="name" type="category" stroke={axisStroke} fontSize={10} width={120} tick={{ fill: axisStroke }} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(val) => [`${val}%`]} labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="QBank Acc" fill={AMBER} radius={[0, 3, 3, 0]} />
                    <Bar dataKey="PYQ Acc" fill={VIOLET} radius={[0, 3, 3, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Links */}
          <div className="flex items-center gap-3 px-5 pb-4">
            <Link to={`/subjects/${subject.subject_id}`} className="text-xs mono text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors">
              View subject <ArrowUpRight className="w-3 h-3" />
            </Link>
            <Link to={`/questions?subject_id=${subject.subject_id}`} className="text-xs mono text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors">
              Practice QBank <ArrowUpRight className="w-3 h-3" />
            </Link>
            <Link to={`/pyqs?subject_id=${subject.subject_id}`} className="text-xs mono text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors">
              Solve PYQs <ArrowUpRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      )}
    </section>
  );
};

/* ─── mini horizontal progress bar in header ─── */
const MiniBar = ({ label, pct, acc, solved }) => (
  <div className="w-24">
    <div className="flex items-center justify-between text-[9px] mono text-muted-foreground mb-0.5">
      <span>{label}</span>
      <span className={accTone(acc, solved > 0)}>{acc}%</span>
    </div>
    <div className="h-1.5 rounded-full bg-muted-foreground/10 overflow-hidden">
      <div className={`h-full rounded-full transition-all ${accBg(acc, solved > 0)}`} style={{ width: `${pct}%` }} />
    </div>
  </div>
);

/* ─── mini stat block inside expanded card ─── */
const MiniStat = ({ label, value, sub, tone }) => (
  <div className="rounded-md border border-border/60 px-3 py-2.5 bg-background/30">
    <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{label}</div>
    <div className={`text-lg font-bold mono mt-0.5 ${tone || ""}`}>{value}</div>
    {sub && <div className="text-[10px] mono text-muted-foreground">{sub}</div>}
  </div>
);


/* ──────────────────────────────────────────
   MAIN ANALYTICS COMPONENT
   ────────────────────────────────────────── */
export default function Analytics() {
  const [topicDataCache, setTopicDataCache] = useState({});
  const [expandedSubjects, setExpandedSubjects] = useState(new Set());
  const { data } = useDashboard();
  const loadSubjectAnalytics = useSubjectAnalyticsLoader();

  const toggleSubject = async (sid) => {
    setExpandedSubjects(prev => {
      const next = new Set(prev);
      if (next.has(sid)) { next.delete(sid); } else { next.add(sid); }
      return next;
    });
    // Lazy-load topic breakdown
    if (!topicDataCache[sid]) {
      try {
        const data = await loadSubjectAnalytics(sid);
        setTopicDataCache(prev => ({ ...prev, [sid]: data || [] }));
      } catch { /* silent */ }
    }
  };

  if (!data) return (
    <Layout title="Analytics">
      <div className="text-sm text-muted-foreground">Loading…</div>
    </Layout>
  );

  const s = data.summary;
  const subjects = data.subjects;

  /* ── Derived data for overview charts ── */
  const solvedChartData = subjects.map(sub => ({
    name: sub.subject.name.length > 12 ? sub.subject.name.slice(0, 10) + "…" : sub.subject.name,
    fullName: sub.subject.name,
    QBank: sub.qb.solved,
    PYQ: sub.pyq.solved,
  }));

  const accChartData = subjects.map(sub => ({
    name: sub.subject.name.length > 12 ? sub.subject.name.slice(0, 10) + "…" : sub.subject.name,
    fullName: sub.subject.name,
    "QBank Acc": sub.qb.accuracy,
    "PYQ Acc": sub.pyq.accuracy,
  }));

  /* radar data for QBank accuracy comparison */
  const radarData = subjects
    .filter(sub => sub.qb.solved > 0 || sub.pyq.solved > 0)
    .map(sub => ({
      subject: sub.subject.name.split(" ")[0],
      QBank: sub.qb.accuracy,
      PYQ: sub.pyq.accuracy,
    }));

  /* completion pie data */
  const totalQB = subjects.reduce((a, s) => a + s.qb.total, 0);
  const solvedQB = subjects.reduce((a, s) => a + s.qb.solved, 0);
  const totalPYQ = subjects.reduce((a, s) => a + s.pyq.total, 0);
  const solvedPYQ = subjects.reduce((a, s) => a + s.pyq.solved, 0);

  /* subject distribution pie */
  const subjectDistribution = subjects
    .filter(sub => sub.qb.solved + sub.pyq.solved > 0)
    .map(sub => ({ name: sub.subject.name, value: sub.qb.solved + sub.pyq.solved }));

  /* weakest + strongest subjects */
  const subjectsWithAcc = subjects
    .filter(sub => sub.qb.solved + sub.pyq.solved > 0)
    .map(sub => {
      const totalSolved = sub.qb.solved + sub.pyq.solved;
      const weightedAcc = totalSolved > 0
        ? Math.round(((sub.qb.accuracy * sub.qb.solved) + (sub.pyq.accuracy * sub.pyq.solved)) / totalSolved * 10) / 10
        : 0;
      return { ...sub, weightedAcc };
    })
    .sort((a, b) => a.weightedAcc - b.weightedAcc);

  const weakest = subjectsWithAcc.slice(0, 3);
  const strongest = [...subjectsWithAcc].reverse().slice(0, 3);

  return (
    <Layout title="Analytics">
      <div className="space-y-10">
        {/* ─── Page Header ─── */}
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Insights</div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-xl">
            Deep dive into your GATE preparation progress. Track accuracy, identify weak spots, and monitor your growth across every subject and topic.
          </p>
        </div>

        {/* ─── Section 1: Global Summary Cards ─── */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">Overall Progress</div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <Stat icon={BookCheck} label="QBank Solved" value={s.questions_solved} sub={`of ${totalQB} total`} />
            <Stat icon={History} label="PYQs Solved" value={s.pyqs_solved} sub={`of ${totalPYQ} total`} />
            <Stat icon={Target} label="QBank Accuracy" value={s.question_accuracy} suffix="%" />
            <Stat icon={TrendingUp} label="PYQ Accuracy" value={s.pyq_accuracy} suffix="%" />
            <Stat icon={AlertOctagon} label="Mistakes Logged" value={s.total_mistakes} sub="review in Mistake Lab" />
            <Stat icon={BarChart3} label="Completion" value={totalQB + totalPYQ > 0 ? Math.round(((solvedQB + solvedPYQ) / (totalQB + totalPYQ)) * 100) : 0} suffix="%" sub={`${solvedQB + solvedPYQ}/${totalQB + totalPYQ} items`} />
          </div>
        </div>

        {/* ─── Section 2: Accuracy Gauges + Radar ─── */}
        <div className="grid lg:grid-cols-3 gap-5">
          <div className="border border-border rounded-lg p-5 flex items-center justify-center gap-8">
            <AccuracyGauge label="QBank" value={s.question_accuracy} fill={EMERALD} />
            <AccuracyGauge label="PYQ" value={s.pyq_accuracy} fill={BLUE} />
          </div>

          {radarData.length >= 3 && (
            <div className="border border-border rounded-lg p-5 lg:col-span-2">
              <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">Accuracy Comparison · Radar</div>
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData} outerRadius="75%">
                  <PolarGrid stroke="hsl(var(--border))" />
                  <PolarAngleAxis dataKey="subject" stroke={axisStroke} fontSize={10} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} stroke={axisStroke} fontSize={9} />
                  <Radar name="QBank" dataKey="QBank" stroke={EMERALD} fill={EMERALD} fillOpacity={0.2} strokeWidth={2} />
                  <Radar name="PYQ" dataKey="PYQ" stroke={BLUE} fill={BLUE} fillOpacity={0.15} strokeWidth={2} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(val) => [`${val}%`]} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* ─── Section 3: Overview bar charts ─── */}
        <div className="grid lg:grid-cols-2 gap-5">
          <div className="border border-border rounded-lg p-5">
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">Questions Solved · by subject</div>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={solvedChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="name" stroke={axisStroke} fontSize={10} />
                <YAxis stroke={axisStroke} fontSize={10} />
                <Tooltip contentStyle={tooltipStyle} labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="QBank" fill={EMERALD} radius={[3, 3, 0, 0]} />
                <Bar dataKey="PYQ" fill={BLUE} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="border border-border rounded-lg p-5">
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">Accuracy · by subject</div>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={accChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="name" stroke={axisStroke} fontSize={10} />
                <YAxis stroke={axisStroke} fontSize={10} domain={[0, 100]} unit="%" />
                <Tooltip contentStyle={tooltipStyle} labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label} formatter={(val) => [`${val}%`]} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="QBank Acc" fill={AMBER} radius={[3, 3, 0, 0]} />
                <Bar dataKey="PYQ Acc" fill={VIOLET} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* ─── Section 4: Effort Distribution + Strengths & Weaknesses ─── */}
        <div className="grid lg:grid-cols-3 gap-5">
          {/* Pie Chart */}
          {subjectDistribution.length > 0 && (
            <div className="border border-border rounded-lg p-5">
              <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">Effort Distribution</div>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={subjectDistribution}
                    cx="50%" cy="50%"
                    innerRadius={50} outerRadius={85}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, percent }) => `${name.split(" ")[0]} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                    fontSize={9}
                  >
                    {subjectDistribution.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} formatter={(val, name) => [`${val} solved`, name]} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Weakest Subjects */}
          <div className="border border-border rounded-lg p-5">
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">⚠ Needs Improvement</div>
            {weakest.length === 0 ? (
              <div className="text-xs text-muted-foreground">Solve some questions to see weak areas.</div>
            ) : (
              <div className="space-y-3">
                {weakest.map((sub, i) => (
                  <Link key={sub.subject.subject_id} to={`/subjects/${sub.subject.subject_id}`} className="block group">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded bg-red-500/10 text-red-400 text-[10px] font-bold flex items-center justify-center border border-red-500/20">{i + 1}</div>
                        <span className="text-sm font-medium group-hover:text-foreground transition-colors">{sub.subject.name}</span>
                      </div>
                      <span className={`text-xs mono font-semibold ${accTone(sub.weightedAcc, true)}`}>{sub.weightedAcc}%</span>
                    </div>
                    <div className="h-1 rounded-full bg-muted-foreground/10 overflow-hidden mt-1.5 ml-7">
                      <div className="h-full rounded-full bg-red-400/70" style={{ width: `${sub.weightedAcc}%` }} />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Strongest Subjects */}
          <div className="border border-border rounded-lg p-5">
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">✓ Strongest Subjects</div>
            {strongest.length === 0 ? (
              <div className="text-xs text-muted-foreground">Solve some questions to see your strengths.</div>
            ) : (
              <div className="space-y-3">
                {strongest.map((sub, i) => (
                  <Link key={sub.subject.subject_id} to={`/subjects/${sub.subject.subject_id}`} className="block group">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-bold flex items-center justify-center border border-emerald-500/20">{i + 1}</div>
                        <span className="text-sm font-medium group-hover:text-foreground transition-colors">{sub.subject.name}</span>
                      </div>
                      <span className={`text-xs mono font-semibold ${accTone(sub.weightedAcc, true)}`}>{sub.weightedAcc}%</span>
                    </div>
                    <div className="h-1 rounded-full bg-muted-foreground/10 overflow-hidden mt-1.5 ml-7">
                      <div className="h-full rounded-full bg-emerald-400/70" style={{ width: `${sub.weightedAcc}%` }} />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ─── Section 5: Per-Subject Deep Dive ─── */}
        <div className="space-y-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Deep Dive</div>
            <h2 className="text-xl font-semibold tracking-tight mt-1">Subject-wise Breakdown</h2>
            <p className="text-xs text-muted-foreground mt-0.5">Click any subject to expand topic-level charts and statistics.</p>
          </div>
          <div className="space-y-3">
            {subjects.map(row => (
              <SubjectAnalyticsCard
                key={row.subject.subject_id}
                row={row}
                topicData={topicDataCache[row.subject.subject_id]}
                open={expandedSubjects.has(row.subject.subject_id)}
                onToggle={() => toggleSubject(row.subject.subject_id)}
              />
            ))}
          </div>
        </div>
      </div>
    </Layout>
  );
}
