# The effect of luck and timing on savings, or: How I learned to turn off the default target date option in my 401k
## And: Claude Code Demo 

This repo was designed to show students how to replicate the analysis in [a post](https://x.com/jesusferna7026/status/2023742455204520249?s=12) by Jesús Fernández-Villaverde.

1. Go to the [claude-long-prompt](https://github.com/donbowen/RetirementAndSavingPolicy/tree/claude-long-prompt) branch to see Claude 4.5 Sonnet's (an "old", "midle" model) successful replication.
2. The [history](https://github.com/donbowen/RetirementAndSavingPolicy/commits/claude-long-prompt/) of that branch shows exactly the steps I followed:
   1. Create a new folder on my computer and open in VS Code. 
   2. Copy in README.md created at [Claude.ai](claude.ai). The chat is [here](https://claude.ai/share/81498b7e-7d82-4c6d-b519-3689ae752225) and is just his tweet plus "Design a prompt I can give to an LLM, to replicate this analysis. Use all the best practices about guidance on checkpoints and verification, and breaking the problem into pieces. Include other best practices as well. Don’t include in the prompt the conclusion the author arrives at."
   3. CLAUDE.md is basically just the path to my python executable, though Claude Code will find that if you don't make this file.
   4. Open the VS Code Claude Code extension. (Or point the app at the folder.)
   5. "The readme file contains an analysis plan. The Claude.md file has a few notes about working on this computer. Please execute the research. Ask questions as needed, and ensure the checkpoints are satisfied before proceeding."
   6. Wait. I wrote [comments as it was going](https://github.com/donbowen/RetirementAndSavingPolicy/blob/claude-long-prompt/prompt_log.md) which included "yuck" and "dumbass" and "Well, Damn"
   7. Done.

## Lessons 
1. In 34/35 years, you would have been better off with 100% of your retirement in equities rather than a "target-date" fund that slowly increases bond exposure:
   ![](https://github.com/donbowen/RetirementAndSavingPolicy/blob/claude-long-prompt/chart1_terminal_wealth.png?raw=true)
1. For more lessons on the finance/econ angle, see [Jesus's original post](https://x.com/jesusferna7026/status/2023742455204520249?s=12)
2. Prompts for Claude Code and Codex matter. 
   1. Refine your prompt for Claude Code/Codex on Claude.ai or Chatgpt.com. The more details, the better, and ask for checkpoints and modularity.
   2. The other branch in this folder shows the result of [a shorter/worse prompt](https://github.com/donbowen/RetirementAndSavingPolicy/tree/short_prompt_codex). Codex 5.3 spun its wheels quite a bit on even getting the file and I stopped it after it ask for permissions to try a 4th thing to get the data. So the output was: nothing. 
