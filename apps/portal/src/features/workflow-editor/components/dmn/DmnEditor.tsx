/**
 * Wrapper around dmn-js DmnModeler.
 *
 * dmn-js is similar to bpmn-js but targets DMN 1.3 decision tables.
 * The modeler is mounted into a container ref and destroyed on unmount.
 */
import { useEffect, useRef, useImperativeHandle, forwardRef } from "react";

// @ts-expect-error no bundled types
import DmnModeler from "dmn-js/lib/Modeler";

export interface DmnEditorHandle {
  getXml: () => Promise<string>;
}

interface Props {
  xml?: string;
  onChange?: (xml: string) => void;
}

const EMPTY_DMN = `<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/"
             xmlns:dmndi="https://www.omg.org/spec/DMN/20191111/DMNDI/"
             xmlns:dc="http://www.omg.org/spec/DMN/20180521/DC/"
             id="Definitions_1"
             name="Decision"
             namespace="http://gxp.internal/dmn">
  <decision id="Decision_1" name="Decision 1">
    <decisionTable id="decisionTable_1">
      <input id="input_1" label="Input">
        <inputExpression id="inputExpression_1" typeRef="string"/>
      </input>
      <output id="output_1" label="Output" typeRef="string"/>
    </decisionTable>
  </decision>
  <dmndi:DMNDI>
    <dmndi:DMNDiagram>
      <dmndi:DMNShape dmnElementRef="Decision_1">
        <dc:Bounds height="80" width="180" x="160" y="100"/>
      </dmndi:DMNShape>
    </dmndi:DMNDiagram>
  </dmndi:DMNDI>
</definitions>`;

const DmnEditor = forwardRef<DmnEditorHandle, Props>(function DmnEditor(
  { xml, onChange },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const modelerRef = useRef<InstanceType<typeof DmnModeler> | null>(null);

  useImperativeHandle(ref, () => ({
    async getXml() {
      if (!modelerRef.current) return "";
      const { xml: exported } = await modelerRef.current.saveXML({ format: true });
      return exported ?? "";
    },
  }));

  useEffect(() => {
    if (!containerRef.current) return;

    const modeler = new DmnModeler({ container: containerRef.current });
    modelerRef.current = modeler;

    modeler.importXML(xml || EMPTY_DMN).catch(console.error);

    if (onChange) {
      modeler.on("commandStack.changed", async () => {
        try {
          const { xml: updated } = await modeler.saveXML({ format: true });
          if (updated) onChange(updated);
        } catch {
          // ignore
        }
      });
    }

    return () => {
      modeler.destroy();
      modelerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

export default DmnEditor;
