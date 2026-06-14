import React from "react";
import ReactDOM from "react-dom/client";
import { RuntimeApp } from "./engine/RuntimeApp";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RuntimeApp />
  </React.StrictMode>
);
