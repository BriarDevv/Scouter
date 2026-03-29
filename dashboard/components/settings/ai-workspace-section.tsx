"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Cpu,
  FileText,
  Heart,
  Loader2,
  Puzzle,
  RotateCcw,
  UserCircle,
  Wrench,
  X,
  XCircle,
  Eye,
  Pencil,
  FolderOpen,
  Save,
} from "lucide-react";
import { sileo } from "sileo";
import { SettingsSectionCard, StatusPill } from "./settings-primitives";
import {
  getAIWorkspaceStatus,
  getAIWorkspaceFile,
  updateAIWorkspaceFile,
  resetAIWorkspaceFile,
} from "@/lib/api/client";
import type {
  AIWorkspaceStatus,
  AIWorkspaceFileStatus,
  AIWorkspaceSkill,
} from "@/types";

// ─── Icon map ────────────────────────────────────────────────────────

const FILE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  soul: Bot,
  identity: UserCircle,
  user: UserCircle,
  heartbeat: Heart,
  tools: Wrench,
  agents: FileText,
};

function getFileIcon(key: string) {
  const lower = key.toLowerCase();
  for (const [k, Icon] of Object.entries(FILE_ICONS)) {
    if (lower.includes(k)) return Icon;
  }
  return FileText;
}

// ─── File Editor Modal ───────────────────────────────────────────────

function FileEditorModal({
  fileKey,
  filename,
  readOnly,
  onClose,
  onSaved,
}: {
  fileKey: string;
  filename: string;
  readOnly: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getAIWorkspaceFile(fileKey)
      .then((data) => {
        if (!active) return;
        setContent(data.content);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Error al cargar archivo.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fileKey]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await sileo.promise(updateAIWorkspaceFile(fileKey, content), {
        loading: { title: "Guardando archivo..." },
        success: { title: `${filename} guardado correctamente` },
        error: (err: unknown) => ({
          title: "Error al guardar",
          description: err instanceof Error ? err.message : "Error desconocido.",
        }),
      });
      onSaved();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[85vh] w-full max-w-3xl flex-col rounded-2xl border border-border bg-card shadow-lg">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-3">
            {readOnly ? (
              <Eye className="h-5 w-5 text-muted-foreground" />
            ) : (
              <Pencil className="h-5 w-5 text-muted-foreground" />
            )}
            <h3 className="text-base font-semibold text-foreground">{filename}</h3>
            {readOnly && <StatusPill label="Solo lectura" tone="neutral" />}
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground transition hover:bg-muted hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando contenido...
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 text-sm text-rose-600">
              <XCircle className="h-4 w-4" />
              {error}
            </div>
          ) : (
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              readOnly={readOnly}
              className="h-96 w-full rounded-xl border border-border bg-muted px-4 py-3 font-mono text-sm text-foreground outline-none transition focus:border-border focus:bg-card disabled:opacity-50"
              spellCheck={false}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium text-foreground/80 transition hover:bg-muted"
          >
            {readOnly ? "Cerrar" : "Cancelar"}
          </button>
          {!readOnly && (
            <button
              onClick={handleSave}
              disabled={saving || loading}
              className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-700 disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              {saving ? "Guardando..." : "Guardar"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Reset Confirm ───────────────────────────────────────────────────

function ResetConfirm({
  filename,
  onConfirm,
  onCancel,
  resetting,
}: {
  filename: string;
  onConfirm: () => void;
  onCancel: () => void;
  resetting: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-lg">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 dark:bg-amber-950/30">
            <RotateCcw className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground">
              Restaurar archivo
            </h3>
            <p className="text-sm text-muted-foreground">
              Restaurar <strong>{filename}</strong> al template por defecto?
            </p>
          </div>
        </div>
        <p className="mb-5 text-xs text-muted-foreground">
          Esta accion reemplazara el contenido actual con el template original.
          Los cambios se perderan.
        </p>
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={resetting}
            className="rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium text-foreground/80 transition hover:bg-muted disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={resetting}
            className="flex items-center gap-2 rounded-xl bg-amber-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-amber-700 disabled:opacity-50"
          >
            {resetting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RotateCcw className="h-4 w-4" />
            )}
            {resetting ? "Restaurando..." : "Restaurar"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── File Card ───────────────────────────────────────────────────────

function FileCard({
  file,
  onEdit,
  onReset,
}: {
  file: AIWorkspaceFileStatus;
  onEdit: () => void;
  onReset: () => void;
}) {
  const Icon = getFileIcon(file.key);

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm transition hover:border-border/80">
      {/* Header */}
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white">
            <Icon className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              {file.filename}
            </h3>
            <p className="text-xs text-muted-foreground">{file.key}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {file.exists ? (
            file.is_empty ? (
              <StatusPill label="Vacio" tone="warning" />
            ) : file.has_valid_structure ? (
              <StatusPill label="Valido" tone="positive" />
            ) : (
              <StatusPill label="Estructura invalida" tone="danger" />
            )
          ) : (
            <StatusPill label="No encontrado" tone="danger" />
          )}
          {file.warnings.length > 0 && (
            <StatusPill
              label={`${file.warnings.length} aviso${file.warnings.length > 1 ? "s" : ""}`}
              tone="warning"
            />
          )}
        </div>
      </div>

      {/* Preview */}
      {file.preview && (
        <div className="mb-3 rounded-xl bg-muted/70 px-3 py-2">
          <p className="line-clamp-2 font-mono text-xs text-muted-foreground">
            {file.preview}
          </p>
        </div>
      )}

      {/* Warnings */}
      {file.warnings.length > 0 && (
        <div className="mb-3 space-y-1">
          {file.warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-1.5">
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-500" />
              <span className="text-xs text-amber-700 dark:text-amber-400">
                {w}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Size info */}
      {file.exists && file.size_bytes != null && (
        <p className="mb-3 text-xs text-muted-foreground">
          {file.size_bytes < 1024
            ? `${file.size_bytes} bytes`
            : `${(file.size_bytes / 1024).toFixed(1)} KB`}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={onEdit}
          className="flex items-center gap-1.5 rounded-xl border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground/80 transition hover:bg-muted"
        >
          {file.editable ? (
            <>
              <Pencil className="h-3.5 w-3.5" />
              Editar
            </>
          ) : (
            <>
              <Eye className="h-3.5 w-3.5" />
              Ver
            </>
          )}
        </button>
        {file.editable && (
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 rounded-xl border border-border bg-card px-3 py-1.5 text-xs font-medium text-amber-700 transition hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-950/20"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Restaurar
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Skill Row ───────────────────────────────────────────────────────

function SkillRow({ skill }: { skill: AIWorkspaceSkill }) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-border bg-muted/70 px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 text-white">
          <Puzzle className="h-4 w-4" />
        </div>
        <div>
          <span className="text-sm font-medium text-foreground">
            {skill.name}
          </span>
          {skill.description && (
            <p className="text-xs text-muted-foreground">{skill.description}</p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        {skill.exists ? (
          <StatusPill label="Activo" tone="positive" />
        ) : (
          <StatusPill label="No encontrado" tone="danger" />
        )}
      </div>
    </div>
  );
}

// ─── Main Section ────────────────────────────────────────────────────

export function AIWorkspaceSection() {
  const [data, setData] = useState<AIWorkspaceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [editingFile, setEditingFile] = useState<{
    key: string;
    filename: string;
    editable: boolean;
  } | null>(null);
  const [resetFile, setResetFile] = useState<{
    key: string;
    filename: string;
  } | null>(null);
  const [resetting, setResetting] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const status = await getAIWorkspaceStatus();
      setData(status);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Error al cargar el workspace de IA."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleReset = async () => {
    if (!resetFile) return;
    setResetting(true);
    try {
      await sileo.promise(resetAIWorkspaceFile(resetFile.key), {
        loading: { title: "Restaurando archivo..." },
        success: { title: `${resetFile.filename} restaurado al template` },
        error: (err: unknown) => ({
          title: "Error al restaurar",
          description: err instanceof Error ? err.message : "Error desconocido.",
        }),
      });
      setResetFile(null);
      void loadData();
    } finally {
      setResetting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-3 rounded-2xl border border-border bg-card p-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Cargando workspace de IA...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-border bg-card p-8">
        <div className="flex items-center gap-2 text-sm text-rose-600">
          <XCircle className="h-4 w-4" />
          {error ?? "No se pudo cargar el workspace de IA."}
        </div>
      </div>
    );
  }

  const presentFiles = data.files.filter((f) => f.exists).length;
  const totalFiles = data.files.length;
  const totalWarnings = data.files.reduce(
    (acc, f) => acc + f.warnings.length,
    0
  );
  const activeSkills = data.skills.filter((s) => s.exists).length;

  return (
    <div className="space-y-6">
      {/* ─── Overview Cards ─────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Workspace path */}
        <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
          <div className="mb-2 flex items-center gap-2">
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">
              Ruta del workspace
            </span>
          </div>
          <p
            className="truncate font-mono text-sm text-foreground"
            title={data.workspace_path}
          >
            {data.workspace_path}
          </p>
        </div>

        {/* OpenClaw status */}
        <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
          <div className="mb-2 flex items-center gap-2">
            <Bot className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">
              OpenClaw
            </span>
          </div>
          <StatusPill
            label={data.openclaw_installed ? "Instalado" : "No instalado"}
            tone={data.openclaw_installed ? "positive" : "danger"}
          />
        </div>

        {/* Onboarding */}
        <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
          <div className="mb-2 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">
              Onboarding
            </span>
          </div>
          <StatusPill
            label={data.onboarding_completed ? "Completado" : "Pendiente"}
            tone={data.onboarding_completed ? "positive" : "warning"}
          />
        </div>

        {/* Files summary */}
        <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
          <div className="mb-2 flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">
              Archivos
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground">
              {presentFiles}/{totalFiles}
            </span>
            {totalWarnings > 0 && (
              <StatusPill
                label={`${totalWarnings} aviso${totalWarnings > 1 ? "s" : ""}`}
                tone="warning"
              />
            )}
          </div>
        </div>
      </div>

      {/* ─── Models ─────────────────────────────────────── */}
      <SettingsSectionCard
        title="Modelos configurados"
        description="Modelos de IA asignados a cada rol del sistema."
        icon={Cpu}
      >
        <div className="space-y-3">
          {(
            [
              { label: "Leader", model: data.models.leader },
              { label: "Executor", model: data.models.executor },
              { label: "Reviewer", model: data.models.reviewer },
            ] as const
          ).map(({ label, model }) => (
            <div
              key={label}
              className="flex items-center justify-between rounded-2xl border border-border bg-muted/70 px-4 py-3"
            >
              <span className="text-sm font-medium text-foreground">
                {label}
              </span>
              <code className="rounded-lg bg-card px-3 py-1.5 text-sm text-foreground/80 shadow-sm">
                {model || "No configurado"}
              </code>
            </div>
          ))}
        </div>
      </SettingsSectionCard>

      {/* ─── Files Grid ─────────────────────────────────── */}
      <SettingsSectionCard
        title="Archivos del workspace"
        description="Archivos de configuracion que definen el comportamiento y la personalidad de la IA."
        icon={FileText}
      >
        <div className="grid gap-4 lg:grid-cols-2">
          {data.files.map((file) => (
            <FileCard
              key={file.key}
              file={file}
              onEdit={() =>
                setEditingFile({
                  key: file.key,
                  filename: file.filename,
                  editable: file.editable,
                })
              }
              onReset={() =>
                setResetFile({ key: file.key, filename: file.filename })
              }
            />
          ))}
        </div>
      </SettingsSectionCard>

      {/* ─── Skills ─────────────────────────────────────── */}
      {data.skills.length > 0 && (
        <SettingsSectionCard
          title="Skills detectados"
          description={`${activeSkills} de ${data.skills.length} skills encontrados en el workspace.`}
          icon={Puzzle}
        >
          <div className="space-y-3">
            {data.skills.map((skill) => (
              <SkillRow key={skill.path} skill={skill} />
            ))}
          </div>
        </SettingsSectionCard>
      )}

      {/* ─── Editor Modal ───────────────────────────────── */}
      {editingFile && (
        <FileEditorModal
          fileKey={editingFile.key}
          filename={editingFile.filename}
          readOnly={!editingFile.editable}
          onClose={() => setEditingFile(null)}
          onSaved={() => void loadData()}
        />
      )}

      {/* ─── Reset Confirm ──────────────────────────────── */}
      {resetFile && (
        <ResetConfirm
          filename={resetFile.filename}
          onConfirm={handleReset}
          onCancel={() => setResetFile(null)}
          resetting={resetting}
        />
      )}
    </div>
  );
}
