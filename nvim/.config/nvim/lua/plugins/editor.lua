-- origin/HEAD 는 clone 시점에 고정되어, main 이 죽고 develop 으로 옮겨간 저장소에서
-- 낡은 브랜치를 가리킨다. 그래서 후보 중 실제 커밋이 가장 최근인 쪽을 기준으로 본다.
-- 자동 감지가 틀리면 vim.g.diffview_base_branch 로 직접 지정.
local BASE_BRANCH_CANDIDATES = { "origin/develop", "origin/main", "origin/master" }

---@return string? base_branch 후보가 하나도 없으면 nil
local function resolve_base_branch()
  if vim.g.diffview_base_branch then return vim.g.diffview_base_branch end

  local repo_dir = vim.fn.expand("%:p:h")
  if repo_dir == "" then repo_dir = vim.uv.cwd() end

  local newest_ref, newest_commit_time = nil, -1
  for _, ref in ipairs(BASE_BRANCH_CANDIDATES) do
    local commit_time = vim.fn.systemlist({ "git", "-C", repo_dir, "log", "-1", "--format=%ct", ref })[1]
    commit_time = vim.v.shell_error == 0 and tonumber(commit_time) or nil
    if commit_time and commit_time > newest_commit_time then
      newest_ref, newest_commit_time = ref, commit_time
    end
  end

  return newest_ref
end

return {
  { "bufferline.nvim", enabled = false },
  {
    "lualine.nvim",
    opts = {
      options = { globalstatus = false },
    },
  },
  {
    "flash.nvim",
    opts = {
      modes = {
        char = { enabled = false },
        search = { enabled = false },
      },
    },
  },
  {
    "sindrets/diffview.nvim",
    dependencies = "nvim-lua/plenary.nvim",
    keys = {
      { "<leader>gf", "<cmd>DiffviewFileHistory<cr>", desc = "Diffvew" },
      { "<leader>gF", "<cmd>DiffviewFileHistory %<cr>", desc = "Diffview (cwd)" },
      { "<leader>go", "<cmd>DiffviewOpen<cr>", desc = "Diffview Open" },
      { "<leader>gc", "<cmd>DiffviewClose<cr>", desc = "Diffview Close" },
      {
        -- gp/gP 는 snacks_picker 의 GitHub PR 목록이 선점하고 있어 gb(ase) 를 쓴다.
        "<leader>gb",
        function()
          local base_branch = resolve_base_branch()
          if not base_branch then
            local candidates = table.concat(BASE_BRANCH_CANDIDATES, ", ")
            vim.notify(
              ("기준 브랜치 없음: %s 중 존재하는 ref 가 없습니다"):format(candidates),
              vim.log.levels.ERROR
            )
            return
          end
          -- 3-dot: merge-base 부터 비교해야 PR 이 보여주는 범위와 일치한다.
          vim.cmd("DiffviewOpen " .. base_branch .. "...HEAD")
        end,
        desc = "Diffview vs Base (PR)",
      },
    },
  },
  {
    "nvim-treesitter",
    opts = {
      highlight = {
        disable = function(_, buf)
          local filesize_limit = 10000 * 1024
          local _, stats = pcall(vim.loop.fs_stat, vim.api.nvim_buf_get_name(buf))

          return stats and stats.size > filesize_limit
        end,
      },
      textobjects = {
        select = {
          enable = true,
          lookahead = true,
          keymaps = {
            ["af"] = "@function.outer",
            ["if"] = "@function.inner",
            ["ac"] = "@class.outer",
            ["ic"] = "@class.inner",
          },
        },
        swap = {
          enable = true,
          swap_next = { ["<C-n>"] = "@parameter.inner" },
          swap_previous = { ["<C-p>"] = "@parameter.inner" },
        },
      },
    },
  },
  {
    "nvim-mini/mini.bufremove",
    keys = {
      { "<A-w>", "<leader>bd", remap = true, desc = "Delete Buffer" },
    },
  },
  {
    "anuvyklack/windows.nvim",
    dependencies = "anuvyklack/middleclass",
    keys = {
      { "<C-w>m", "<cmd>WindowsMaximize<cr>", desc = "Windows Maximize" },
      { "<C-w>=", "<cmd>WindowsEqualize<cr>", desc = "Windows Equalize" },
    },
    opts = {},
  },
  {
    "alexghergh/nvim-tmux-navigation",
    opts = { disable_when_zoomed = true },
    keys = {
      { "<C-h>", "<cmd>NvimTmuxNavigateLeft<cr>", desc = "Navigate Left" },
      { "<C-j>", "<cmd>NvimTmuxNavigateDown<cr>", desc = "Navigate Down" },
      { "<C-k>", "<cmd>NvimTmuxNavigateUp<cr>", desc = "Navigate Up" },
      { "<C-l>", "<cmd>NvimTmuxNavigateRight<cr>", desc = "Navigate Right" },
    },
  },
}
