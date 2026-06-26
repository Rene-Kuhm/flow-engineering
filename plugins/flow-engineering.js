// flow-engineering OpenCode plugin
// Injects a flow status reminder before bash tool calls when flow-engineering/ exists.
// Mirrors graphify.js pattern (one-shot reminder, command namespacing).
import { existsSync } from "fs";
import { join } from "path";

const PLUGIN_VERSION = "0.1.0";

export const FlowEngineeringPlugin = async ({ directory }) => {
  let reminded = false;

  return {
    "tool.execute.before": async (input, output) => {
      if (reminded) return;
      if (!existsSync(join(directory, "flow-engineering"))) return;

      if (input.tool === "bash") {
        const reminder =
          "echo '[flow-engineering " + PLUGIN_VERSION + "] Active changes detected. Run: flow status' && ";
        output.args.command = reminder + output.args.command;
        reminded = true;
      }
    },
  };
};
