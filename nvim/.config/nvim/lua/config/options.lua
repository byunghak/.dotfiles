vim.opt.swapfile = false
vim.opt.backspace = { "start", "eol", "indent" }
vim.opt.spelllang = { "en_us", "cjk" }
vim.opt.spell = true

-- runtime ftplugin/go.vim 이 ]] [[ 를 func/type 섹션 이동으로 덮어써
-- LazyVim 의 Next/Prev Reference 가 Go 에서만 동작하지 않는 것을 막는다.
vim.g.no_go_maps = true
