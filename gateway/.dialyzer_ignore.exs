# Dialyzer false positives that are explicitly understood and accepted.
#
# call_without_opaque on Ecto.Multi chains: on OTP 28, dialyzer treats the
# MapSet inside Ecto.Multi's :names field as an opaque-violating term even for
# perfectly ordinary Multi pipelines. This is an Ecto/OTP interaction, not a
# defect in this codebase; the Multi here is the documented transactional
# message-lifecycle showcase (docs/ARCHITECTURE.md §5).
#
# Breaker no_return + unused_fun: Task.start(fn -> Absinthe.Subscription.publish end)
# inside transition/2 is opaque to Dialyzer — it cannot follow control flow through
# an anonymous function passed to Task.start/1. As a result, transition/2, run_probe/1,
# handle_cast/2, and handle_info/2 all appear to have no local return, and
# schedule_probe/0 appears unused (the guard branch calling it is considered
# unreachable). All functions are correct in production and covered by tests.
[
  {"lib/chat_f1/conversations.ex", :call_without_opaque},
  {"lib/chat_f1/agents/breaker.ex", :no_return},
  {"lib/chat_f1/agents/breaker.ex", :unused_fun}
]
