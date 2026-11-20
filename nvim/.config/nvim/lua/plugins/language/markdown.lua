-- vault 후보 경로: 실제로 있는 폴더만 workspace 로 쓴다
local vaults = {
  { name = "personal", path = "~/vaults/personal" },
  { name = "work", path = "~/vaults/work" },
}

local existing_vaults = vim.tbl_filter(
  function(vault) return vim.fn.isdirectory(vim.fn.expand(vault.path)) == 1 end,
  vaults
)

return {
  {
    "obsidian-nvim/obsidian.nvim",
    ft = "markdown",
    -- workspace 가 하나도 없으면 obsidian.nvim 이 config 에서 실패하므로 로드하지 않는다
    cond = #existing_vaults > 0,
    opts = {
      workspaces = existing_vaults,
    },
  },
}
