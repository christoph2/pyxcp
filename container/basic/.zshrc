
if [ "$TMUX" = "" ]; then
tmux new-session -s xcp_demo -d;
tmux new-window -c /projects/xcplite/C_Demo -t xcp_demo -n XCPlite "./C_Demo.out";
tmux new-window -c /projects/xcp-examples -t xcp_demo -n pyxcp
tmux attach
fi

export ZSH_TMUX_AUTOSTART=true
export ZSH_TMUX_AUTOSTART_ONCE=true
export ZSH_TMUX_AUTOCONNECT=true

# export LDLIBS='-lm'

export PYXCP_HANDLE_ERRORS=TRUE

[[ $fpath = *user-functions* ]] || export fpath=(~/.local/user-functions $fpath)

# Uncomment the following line to automatically update without prompting.
DISABLE_UPDATE_PROMPT="true"

# Uncomment the following line to enable command auto-correction.
ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
COMPLETION_WAITING_DOTS="true"

autoload -U compinit && compinit -u

# Preferred editor for local and remote sessions
 if [[ -n $SSH_CONNECTION ]]; then
   export EDITOR='nano'
 else
   export EDITOR='nano'
 fi

bindkey  "^[[H"   beginning-of-line
bindkey  "^[[F"   end-of-line
setopt noextendedhistory
setopt noincappendhistory
setopt nosharehistory
setopt histfindnodups
setopt histverify
setopt cshnullglob
setopt extendedglob
setopt chaselinks
setopt pushdignoredups

autoload -U age

zstyle ':completion: * ' use-cache on
zstyle ':completion: * ' cache-path ~/.zsh/cache

zstyle ':completion: * ' completer _complete _match _approximate
zstyle ':completion: * :match: * ' original only
zstyle ':completion: * :approximate: * ' max-errors 1 numeric

zstyle ':completion: * :functions' ignored-patterns '_ * '

zstyle ':completion: * : * :kill: * ' menu yes select
zstyle ':completion: * :kill: * ' force-list always

if [[ -r ~/.aliasrc ]]; then
    . ~/.aliasrc
fi
