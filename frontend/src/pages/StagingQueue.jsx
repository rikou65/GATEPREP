import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertOctagon, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import Layout from "@/components/Layout";

export default function StagingQueue() {
  const [items, setItems] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    fetchStaging();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchStaging = async () => {
    try {
      const res = await api.get("/admin/staging");
      setItems(res.data?.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchJobs = async () => {
    try {
      const res = await api.get("/admin/import/jobs");
      setJobs(res.data?.data || []);
    } catch (e) {}
  };

  const handleBulkApprove = async () => {
    setProcessing(true);
    try {
      await api.post("/admin/staging/bulk-approve");
      toast.success("Successfully approved ready items");
      fetchStaging();
    } catch (e) {
      toast.error("Bulk approval failed");
    } finally {
      setProcessing(false);
    }
  };

  const handleDiscard = async (id) => {
    try {
      await api.delete(`/admin/staging/${id}`);
      setItems(items.filter(i => i.staging_id !== id));
      toast.success("Item discarded");
    } catch (e) {
      toast.error("Failed to discard item");
    }
  };

  const handleApproveSingle = async (item) => {
    try {
      await api.post("/admin/staging/approve-specific", { staging_id: item.staging_id });
      setItems(items.filter(i => i.staging_id !== item.staging_id));
      toast.success("Item manually approved");
    } catch (e) {
      toast.error("Failed to approve item");
    }
  };

  const readyItems = items.filter(i => i.status === "READY");
  const orphanedItems = items.filter(i => i.status !== "READY");
  const activeJobs = jobs.filter(j => j.status === "PROCESSING");

  if (loading) {
    return (
      <Layout title="Staging Queue">
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="OCR Staging Queue">
      <div className="max-w-5xl mx-auto space-y-8">
        
        {/* Active Jobs / Progress Bar */}
        {activeJobs.map(job => (
          <div key={job.job_id} className="p-4 bg-primary/5 border border-primary/20 rounded-xl space-y-3">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2 font-medium">
                <RefreshCw className="w-4 h-4 animate-spin text-primary" />
                Ingesting: {job.filename}
              </div>
              <div className="text-muted-foreground">
                {job.progress} / {job.total_pages} pages processed
              </div>
            </div>
            <div className="h-2 w-full bg-primary/10 rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary transition-all duration-500" 
                style={{ width: `${(job.progress / job.total_pages) * 100 || 0}%` }}
              />
            </div>
          </div>
        ))}

        {/* Header Stats */}
        <div className="flex items-center justify-between p-6 bg-card border border-border rounded-xl">
          <div>
            <h2 className="text-xl font-bold">Review Pipeline</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {items.length} items extracted from PDFs.
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-2xl font-bold text-emerald-500">{readyItems.length}</div>
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Ready</div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-rose-500">{orphanedItems.length}</div>
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Orphans</div>
            </div>

            <Button 
              onClick={handleBulkApprove} 
              disabled={readyItems.length === 0 || processing}
              className="ml-4 h-12 px-6 bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              {processing ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : <CheckCircle2 className="w-5 h-5 mr-2" />}
              Approve All 100% Matches
            </Button>
          </div>
        </div>

        {/* Orphan Triage */}
        {orphanedItems.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2 text-rose-500">
              <AlertOctagon className="w-5 h-5" />
              Action Required: High Discrepancy
            </h3>

            <div className="grid gap-4">
              {orphanedItems.map(item => (
                <div key={item.staging_id} className="p-6 border border-rose-500/20 bg-rose-500/5 rounded-lg space-y-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="bg-background">{item.extracted_id}</Badge>
                      <Badge variant="destructive" className="bg-rose-500/20 text-rose-500">
                        {item.status === "ORPHANED_QUESTION" ? "Missing Solution" : "Missing Question Body"}
                      </Badge>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => handleApproveSingle(item)} className="text-emerald-600 border-emerald-600/30 hover:bg-emerald-600/10">
                        Force Approve
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDiscard(item.staging_id)} className="text-rose-500 hover:bg-rose-500/10">
                        Discard
                      </Button>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                      {item.question_text || "(No question text extracted)"}
                    </p>
                    
                    {item.options?.length > 0 && (
                      <div className="grid grid-cols-2 gap-2">
                        {item.options.map((opt, idx) => (
                          <div key={idx} className="px-3 py-2 text-xs border border-border bg-background rounded-md text-muted-foreground">
                            {String.fromCharCode(65 + idx)}. {opt}
                          </div>
                        ))}
                      </div>
                    )}

                    {item.solution_text && (
                      <div className="mt-4 p-3 bg-background/50 border border-border rounded-md italic text-xs text-muted-foreground">
                        <strong>Partial Solution:</strong> {item.solution_text}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Ready Preview */}
        {readyItems.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-muted-foreground">Preview: Ready for DB</h3>
            <div className="grid gap-3 opacity-60">
              {readyItems.slice(0, 5).map(item => (
                <div key={item.staging_id} className="p-4 border border-border bg-card rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-4 overflow-hidden">
                    <span className="font-mono text-sm shrink-0">{item.extracted_id}</span>
                    <span className="text-sm text-muted-foreground truncate">{item.question_text}</span>
                  </div>
                  <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 shrink-0 ml-4">100% Match</Badge>
                </div>
              ))}
              {readyItems.length > 5 && (
                <div className="text-center text-sm text-muted-foreground py-2">
                  + {readyItems.length - 5} more items will be approved
                </div>
              )}
            </div>
          </div>
        )}

        {items.length === 0 && activeJobs.length === 0 && (
          <div className="text-center py-20 border border-dashed border-border rounded-xl">
            <div className="inline-flex w-12 h-12 rounded-full bg-muted items-center justify-center mb-4">
              <CheckCircle2 className="w-6 h-6 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-medium">Queue is empty</h3>
            <p className="text-sm text-muted-foreground mt-1">Start a new import to see items here.</p>
          </div>
        )}
      </div>
    </Layout>
  );
}
