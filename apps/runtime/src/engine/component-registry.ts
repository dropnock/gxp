/**
 * Closed-set registry: maps GXP component type strings to React components.
 * This is the security boundary — only components listed here can render
 * in published apps. No eval(), no dynamic imports, no script injection.
 *
 * The set of valid types here must match VALID_COMPONENT_TYPES in
 * services/app-service/app/services/builder.py — both are enforced
 * independently (builder strips unknown types at publish; renderer ignores
 * them at runtime).
 */
import type React from "react";
import { GxpButton }    from "../components/GxpButton";
import { GxpCard }      from "../components/GxpCard";
import { GxpContainer } from "../components/GxpContainer";
import { GxpForm }      from "../components/GxpForm";
import { GxpTable }     from "../components/GxpTable";
import { GxpText }      from "../components/GxpText";

type GxpComponent = React.ComponentType<Record<string, unknown> & { children?: React.ReactNode }>;

export const registry: Record<string, GxpComponent> = {
  "gxp-text":      GxpText      as GxpComponent,
  "gxp-button":    GxpButton    as GxpComponent,
  "gxp-form":      GxpForm      as GxpComponent,
  "gxp-table":     GxpTable     as GxpComponent,
  "gxp-card":      GxpCard      as GxpComponent,
  "gxp-container": GxpContainer as GxpComponent,
};
