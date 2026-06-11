import { type CodegenConfig } from "@graphql-codegen/cli";

/**
 * Generates typed Apollo hooks from the committed gateway SDL.
 *
 * `schema.graphql` is regenerated from the gateway with:
 *   cd ../gateway && mix absinthe.schema.sdl --schema ChatF1Web.Schema ../web/schema.graphql
 *
 * CI runs `npm run codegen && git diff --exit-code` to catch drift between
 * the committed schema, the documents, and the generated types.
 */
const config: CodegenConfig = {
  schema: "schema.graphql",
  documents: ["src/graphql/**/*.graphql"],
  generates: {
    "src/graphql/generated.ts": {
      plugins: ["typescript", "typescript-operations", "typescript-react-apollo"],
      config: {
        withHooks: true,
        enumsAsTypes: true,
        scalars: { DateTime: "string" },
        dedupeOperationSuffix: true,
      },
    },
    "src/graphql/possible-types.ts": {
      plugins: ["fragment-matcher"],
      config: { useExplicitTyping: true },
    },
  },
  hooks: { afterAllFileWrite: [] },
};

export default config;
