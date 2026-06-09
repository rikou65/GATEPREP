import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { FolderArchive, Plus, ExternalLink, Trash2 } from "lucide-react";
import { toast } from "sonner";

const TYPES = ["Books", "Notes", "Question Banks", "PYQ Collections", "Formula Sheets", "Reference Material"];

export default function Resources() {
  const [items, setItems] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState({ subject_id: "", resource_type: "" });
  const [form, setForm] = useState({ title: "", subject_id: "", resource_type: "Notes", external_url: "" });

  const load = () => {
    const params = {};
    Object.entries(filter).forEach(([k, v]) => { if (v) params[k] = v; });
    api.get("/resources", { params }).then(r => setItems(r.data?.data || []));
  };
  useEffect(() => { api.get("/subjects").then(r => setSubjects(r.data?.data || [])); }, []);
  useEffect(load, [filter]); // eslint-disable-line

  const submit = async () => {
    if (!form.title || !form.subject_id) return toast.error("Fill required fields");
    await api.post("/resources", form);
    setOpen(false); setForm({ title: "", subject_id: "", resource_type: "Notes", external_url: "" });
    load(); toast.success("Resource added");
  };
  const remove = async (id) => { await api.delete(`/resources/${id}`); load(); };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Library</div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Resources</h1>
          <p className="text-sm text-muted-foreground mt-1">Link external PDFs (Google Drive, Dropbox, etc.). Metadata only — files stay where you stored them.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild><Button data-testid="add-resource-btn"><Plus className="w-4 h-4 mr-1" /> Add resource</Button></DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader><DialogTitle>Add Resource</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Input placeholder="Title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} data-testid="resource-title-input" />
              <select value={form.subject_id} onChange={e => setForm({ ...form, subject_id: e.target.value })} className="w-full h-10 px-3 text-sm bg-transparent border border-border rounded-md" data-testid="resource-subject-select">
                <option value="">Subject</option>
                {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
              </select>
              <select value={form.resource_type} onChange={e => setForm({ ...form, resource_type: e.target.value })} className="w-full h-10 px-3 text-sm bg-transparent border border-border rounded-md">
                {TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
              <Input placeholder="External URL (Google Drive, Dropbox…)" value={form.external_url} onChange={e => setForm({ ...form, external_url: e.target.value })} />
            </div>
            <DialogFooter><Button onClick={submit} data-testid="save-resource-btn">Save</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex gap-2">
        <select value={filter.subject_id} onChange={e => setFilter({ ...filter, subject_id: e.target.value })} className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">All subjects</option>
          {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
        </select>
        <select value={filter.resource_type} onChange={e => setFilter({ ...filter, resource_type: e.target.value })} className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">All types</option>
          {TYPES.map(t => <option key={t}>{t}</option>)}
        </select>
      </div>

      {items.length === 0 ? (
        <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-12 text-center flex flex-col items-center gap-2">
          <FolderArchive className="w-5 h-5" /> No resources yet.
        </div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-border">
              <tr className="text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                <th className="p-3 font-medium">Title</th>
                <th className="p-3 font-medium">Type</th>
                <th className="p-3 font-medium">Subject</th>
                <th className="p-3 font-medium">Link</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {items.map(r => {
                const sub = subjects.find(s => s.subject_id === r.subject_id);
                return (
                  <tr key={r.resource_id} className="border-b border-border" data-testid={`resource-${r.resource_id}`}>
                    <td className="p-3">{r.title}</td>
                    <td className="p-3 text-xs mono text-muted-foreground">{r.resource_type}</td>
                    <td className="p-3 text-xs text-muted-foreground">{sub?.name}</td>
                    <td className="p-3">
                      {r.external_url ? (
                        <a href={r.external_url} target="_blank" rel="noreferrer" className="text-xs inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">
                          Open <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : <span className="text-xs text-muted-foreground">—</span>}
                    </td>
                    <td className="p-3 text-right">
                      <button onClick={() => remove(r.resource_id)} data-testid={`delete-resource-${r.resource_id}`} className="text-muted-foreground hover:text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
