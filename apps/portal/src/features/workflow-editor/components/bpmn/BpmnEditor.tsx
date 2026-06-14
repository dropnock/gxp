/**
 * Wrapper around bpmn-js BpmnModeler.
 *
 * Mounts the modeler into a container div via a ref. The caller controls
 * the XML via the `xml` prop and receives updates via `onChange`.
 *
 * On unmount the modeler is destroyed to free DOM listeners.
 */
import { useEffect, useRef, useImperativeHandle, forwardRef } from "react";

// bpmn-js ships as CJS/UMD — import the modeler entry point.
// @ts-expect-error no bundled types in all versions
import BpmnModeler from "bpmn-js/lib/Modeler";

export interface BpmnEditorHandle {
  getXml: () => Promise<string>;
}

interface Props {
  xml?: string;
  onChange?: (xml: string) => void;
  readOnly?: boolean;
}

const EMPTY_DIAGRAM = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  targetNamespace="http://gxp.internal/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1"/>
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
        <dc:Bounds height="36.0" width="36.0" x="173.0" y="102.0"/>
      </bpmndi:BPMNShape>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>`;

const BpmnEditor = forwardRef<BpmnEditorHandle, Props>(function BpmnEditor(
  { xml, onChange, readOnly = false },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const modelerRef = useRef<InstanceType<typeof BpmnModeler> | null>(null);

  useImperativeHandle(ref, () => ({
    async getXml() {
      if (!modelerRef.current) return "";
      const { xml: exported } = await modelerRef.current.saveXML({ format: true });
      return exported ?? "";
    },
  }));

  useEffect(() => {
    if (!containerRef.current) return;

    const modeler = new BpmnModeler({
      container: containerRef.current,
      keyboard: { bindTo: window },
    });
    modelerRef.current = modeler;

    const initialXml = xml || EMPTY_DIAGRAM;
    modeler.importXML(initialXml).catch(console.error);

    if (onChange) {
      modeler.on("commandStack.changed", async () => {
        try {
          const { xml: updated } = await modeler.saveXML({ format: true });
          if (updated) onChange(updated);
        } catch {
          // ignore serialization errors during partial edits
        }
      });
    }

    return () => {
      modeler.destroy();
      modelerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When xml prop changes externally (e.g. loading a saved definition), re-import.
  useEffect(() => {
    if (modelerRef.current && xml) {
      modelerRef.current.importXML(xml).catch(console.error);
    }
  }, [xml]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", border: "1px solid #d1d5db", borderRadius: 4 }}
    />
  );
});

export default BpmnEditor;
