# Dialyzer false positives that are explicitly understood and accepted.
#
# call_without_opaque on Ecto.Multi chains: on OTP 28, dialyzer treats the
# MapSet inside Ecto.Multi's :names field as an opaque-violating term even for
# perfectly ordinary Multi pipelines. This is an Ecto/OTP interaction, not a
# defect in this codebase; the Multi here is the documented transactional
# message-lifecycle showcase (docs/ARCHITECTURE.md §5).
[
  {"lib/chat_f1/conversations.ex", :call_without_opaque}
]
