/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "no-frontend-to-database",
      comment: "Frontend must not directly access the database layer.",
      severity: "error",
      from: { path: "^src/frontend" },
      to: { path: "^src/database|^src/db" },
    },
    {
      name: "no-circular",
      comment: "Circular dependencies indicate design issues.",
      severity: "warn",
      from: {},
      to: { circular: true },
    },
    {
      name: "no-orphans",
      comment: "Orphaned modules suggest dead code.",
      severity: "info",
      from: { orphan: true, pathNot: "^(src/index|test)" },
      to: {},
    },
  ],
  allowed: [
    {
      comment: "Frontend may call backend API services.",
      from: { path: "^src/frontend" },
      to: { path: "^src/(api|services)" },
    },
    {
      comment: "Backend services may access database layer.",
      from: { path: "^src/(api|services)" },
      to: { path: "^src/(database|db|models)" },
    },
    {
      comment: "Shared utilities may be used anywhere.",
      from: {},
      to: { path: "^src/(utils|common|shared)" },
    },
  ],
  options: {
    doNotFollow: {
      path: "node_modules",
    },
    includeOnly: "^src",
    tsPreCompilationDeps: true,
    combinedDependencies: false,
    reporterOptions: {
      dot: {
        collapsePattern: "node_modules/(?:@[^/]+/[^/]+|[^/]+)",
      },
    },
    // LOGHOUSE integration: output edges for drift detection
    outputTo: "/tmp/loghouse/dependency-edges.json",
    outputType: "json",
  },
};
