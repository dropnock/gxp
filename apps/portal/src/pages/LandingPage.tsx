import { Navigate } from "react-router-dom";
import {
  LayoutGrid,
  GitBranch,
  FolderKanban,
  FolderLock,
  ChevronRight,
  Shield,
  Server,
  FileCheck,
  Mail,
} from "lucide-react";
import { useAuth } from "../shared/auth";

const FEATURES = [
  {
    Icon: LayoutGrid,
    title: "Low-Code App Builder",
    description:
      "Build and publish internal forms, dashboards, and data interfaces using a drag-and-drop editor. No custom frontend infrastructure required.",
  },
  {
    Icon: GitBranch,
    title: "Workflow Engine",
    description:
      "Model and execute government processes as BPMN diagrams and DMN decision tables, with built-in human-task assignment and approval routing.",
  },
  {
    Icon: FolderKanban,
    title: "Case Management",
    description:
      "Track adaptive cases — permits, investigations, benefits — with participant management, internal notes, linked documents, and a full timeline.",
  },
  {
    Icon: FolderLock,
    title: "Document Store",
    description:
      "Permission-gated document storage with antivirus scanning, versioning, full-text search, and time-limited presigned download links.",
  },
] as const;

const BADGES = [
  { Icon: Shield,    label: "NIST 800-53 / FedRAMP" },
  { Icon: Server,    label: "Air-Gap Deployable" },
  { Icon: FileCheck, label: "Append-Only Audit Log" },
] as const;

export function LandingPage() {
  const { isAuthenticated, isLoading, login } = useAuth();

  if (!isLoading && isAuthenticated) {
    return <Navigate to="/apps" replace />;
  }

  return (
    <main>
      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="landing__hero">
        <div className="container">
          <p className="landing__hero-eyebrow">Government Low-Code Platform</p>
          <h1 className="landing__hero-title">
            Secure infrastructure for modern government services
          </h1>
          <p className="landing__hero-subtitle">
            Build, automate, and manage government applications within a fully
            air-gapped, NIST&nbsp;800-53 compliant environment — without
            standing up bespoke infrastructure for every new initiative.
          </p>

          <div className="landing__hero-actions">
            {!isLoading && (
              <button onClick={login} className="landing__cta">
                Sign In to GXP
                <ChevronRight size={17} aria-hidden="true" />
              </button>
            )}
          </div>

          <div className="landing__badges">
            {BADGES.map(({ Icon, label }) => (
              <span key={label} className="landing__badge">
                <Icon size={12} aria-hidden="true" />
                {label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Capabilities ──────────────────────────────────────────────── */}
      <section className="landing__section">
        <div className="container">
          <p className="landing__section-label">Platform capabilities</p>
          <h2 className="landing__section-title">
            Four pillars — one integrated platform
          </h2>
          <p className="landing__section-sub">
            Replace bespoke tool procurement for every project. GXP provides a
            unified environment covering the full lifecycle of government
            digital services.
          </p>
          <div className="landing__grid">
            {FEATURES.map(({ Icon, title, description }) => (
              <article key={title} className="landing__card">
                <div className="landing__card-icon">
                  <Icon size={20} aria-hidden="true" />
                </div>
                <h3 className="landing__card-title">{title}</h3>
                <p className="landing__card-desc">{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── Support ───────────────────────────────────────────────────── */}
      <section className="landing__section landing__section--alt">
        <div className="container">
          <div className="landing__support">
            <p className="landing__section-label">Support</p>
            <h2 className="landing__support-title">Platform support</h2>
            <p className="landing__support-body">
              GXP is administered by your agency's designated platform team.
              For access requests, role assignments, tenant onboarding, or
              technical assistance, contact your agency's GXP administrator.
              For platform-level outages or critical service issues, escalate
              through your IT service desk.
            </p>
            <p className="landing__support-contact">
              <Mail size={15} aria-hidden="true" />
              Contact your agency's GXP administrator for onboarding and
              support.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
