// Replays a sequence of Bruno steps against a mock `bru` that keeps runtime
// variables across steps and lets the active environment change between them.
// Input (stdin, JSON): {"collection": "<before-request script>",
//   "steps": [{"kind": "token", "env": "DEV", "script": "...", "body": {...}},
//             {"kind": "request", "env": "DEV"}]}
// Output (stdout, JSON): [{"authorization": "Bearer ..."} for each request step].
// The mock has only getEnvName, setVar and getVar: a script that calls anything
// else (setEnvVar, setCollectionVar, a file write) throws, which fails the test.
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const vars = {};
let env = "DEV";
const bru = {
  getEnvName: () => env,
  setVar: (k, v) => { vars[k] = v; },
  getVar: (k) => vars[k],
};
const out = [];
for (const step of input.steps) {
  env = step.env;
  if (step.kind === "token") {
    new Function("bru", "res", step.script)(bru, { body: step.body });
  } else {
    new Function("bru", input.collection)(bru);
    // Bruno leaves an unknown {{name}} in the text as it is (checked in the app)
    const token = vars["access_token"];
    out.push({
      authorization: "Bearer " + (token === undefined ? "{{access_token}}" : token),
    });
  }
}
process.stdout.write(JSON.stringify(out));
