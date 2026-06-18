import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { StaticFileDataSource } from "./datasource";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Missing #root element");
}

// Composition root: the one place that picks the concrete DataSource.
const dataSource = new StaticFileDataSource();

createRoot(root).render(
  <StrictMode>
    <App dataSource={dataSource} />
  </StrictMode>,
);
