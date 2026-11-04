// Mock `bru` and `req` for running generated Bruno scripts under Node.
// Input (stdin, JSON): {"script": "...", "iterations": N, "env": "DEV"}
// Output (stdout, JSON): [{"vars": {...}, "body": <value or null>}, ...]
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = [];
for (let i = 0; i < (input.iterations || 1); i++) {
  const state = { env: input.env || "DEV", vars: {}, body: null };
  const bru = {
    getEnvName: () => state.env,
    setVar: (k, v) => { state.vars[k] = v; },
    getVar: (k) => state.vars[k],
    deleteVar: (k) => { delete state.vars[k]; },
    getAllVars: () => ({ ...state.vars }),
  };
  const req = { setBody: (b) => { state.body = b; }, setHeader: () => {} };
  new Function("bru", "req", input.script)(bru, req);
  out.push({ vars: state.vars, body: state.body });
}
process.stdout.write(JSON.stringify(out));
