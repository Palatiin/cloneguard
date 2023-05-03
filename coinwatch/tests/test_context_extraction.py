test_patch = """
a_len = a_len or 0
b_len = b_len or 0
annotated = []
blame_lines_of_code = len(blame)

if a_len > b_len:
    b_num = b_line
    for a_num in range(a_line, a_line + a_len):
+         prev_commit = blame[a_num - 1][0]
+         if b_num <= blame_lines_of_code and b_num <= b_line + b_len:
+             line_mapping = self._get_line_mapping(prev_commit, commit, filename, b_num)
+
+             annotated.append(Node([b_num, line_mapping], [commit, prev_commit], ["U"]))
+             b_num += 1
+         else:
+             prev_prev_commit = blame[a_num - 1][0]
+             line_mapping = self._get_line_mapping(prev_prev_commit, prev_commit, filename, a_num)
+
+             annotated.append(Node([b_line, line_mapping], [commit, prev_prev_commit], ["D"]))
+     return annotated
+
+ a_num = a_line
+ prev_commit = self.get_first_from_generator(self.repo.rev_list(commit + "~1", filename))[0]
+ for b_num in range(b_line, b_line + b_len):
+     if a_num <= a_line + a_len:
        prev_commit_ = blame[a_num - 1][0]
        line_mapping = self._get_line_mapping(prev_commit_, commit, filename, b_num)

        annotated.append(Node([b_num, line_mapping], [commit, prev_commit_], ["U"]))
        a_num += 1
    else:
        annotated.append(Node([b_num, a_num], [commit, prev_commit], ["A"]))
return annotated
"""

test_patch2 = """
AssertLockHeld(cs_main);
assert(pindex);
assert((pindex->phashBlock == nullptr) ||
    (*pindex->phashBlock == block.GetHash()));
int64_t nTimeStart = GetTimeMicros();
- if (!CheckBlock(block, state, chainparams.GetConsensus(), !fJustCheck, !fJustCheck))
+ if (!CheckBlock(block, state, chainparams.GetConsensus(), !fJustCheck, !fJustCheck)) {
+     if (state.CorruptionPossible()) {
+         return AbortNode(state, “Corrupt block found ...");}}
return error("%s: Consensus::CheckBlock: %s", __func__, ...);
uint256 hashPrevBlock = pindex->pprev == nullptr ? uint256() : ...;
assert(hashPrevBlock == view.GetBestBlock());
if (block.GetHash() == chainparams.GetConsensus().hashGenesisBlock) {
if (!fJustCheck)
"""

test_patch3 = """
AssertLockHeld(cs_main);
assert(pindex);
assert((pindex->phashBlock == nullptr) || (*pindex->phashBlock == block.GetHash()));
int64_t nTimeStart = GetTimeMicros();
-    if (!CheckBlock(block, state, chainparams.GetConsensus(), !fJustCheck, !fJustCheck))
+    if (!CheckBlock(block, state, chainparams.GetConsensus(), !fJustCheck, !fJustCheck)) {
+        if (state.CorruptionPossible()) {
+            return AbortNode(state, "Corrupt block found indicating potential hardware failure; shutting down");
+        }
         return error("%s: Consensus::CheckBlock: %s", __func__, FormatStateMessage(state));
uint256 hashPrevBlock = pindex->pprev == nullptr ? uint256() : pindex->pprev->GetBlockHash();
assert(hashPrevBlock == view.GetBestBlock());
if (block.GetHash() == chainparams.GetConsensus().hashGenesisBlock) {
if (!fJustCheck)
"""

test_patch_exception = """
return error("%s: Consensus::CheckBlock: %s", __func__, ...);
uint256 hashPrevBlock = pindex->pprev == nullptr ? uint256() : ...;
assert(hashPrevBlock == view.GetBestBlock());
if (block.GetHash() == chainparams.GetConsensus().hashGenesisBlock) {
if (!fJustCheck)
"""

test_list_context_extraction = [
    (
        test_patch,
        (
            ["annotated", "blame_lines_of_code", "a_len", "b_line", "a_line"],
            ["prev_commit_", "self._get_line_mapping", "annotated.append", "a_num", "else"],
        ),
    ),
    (
        test_patch2,
        (
            ["AssertLockHeld", "assert", "phashBlock", "block.GetHash", "GetTimeMicros"],
            ["CheckBlock", "hashPrevBlock", "view.GetBestBlock", "chainparams.GetConsensus", "!fJustCheck"],
        ),
    ),
]
