import type {
  AudioAck,
  Rating,
  StageCompletion,
  TerminalInput,
  TerminalOutput,
  TranscriptSegment,
} from "../generated";
import {
  audioAck,
  backendManifest,
  finalizedReport,
  minimalManifest,
  saveConflict,
  transcriptSegment,
} from "../generated/fixture-consumers";

const errorCode: string = saveConflict.error.code;
const service: "postgresql" = backendManifest.services[0];
const empty: never[] = minimalManifest.services;
const audioFrame: AudioAck | TranscriptSegment =
  audioAck.type === "audio_ack" ? audioAck : transcriptSegment;
const isFinal: boolean = transcriptSegment.is_final;
const limitations: string[] = finalizedReport.limitations;
// @ts-expect-error stage completion uses the stage attempt UUID.
const missingAttempt: StageCompletion = { expected_workspace_revision: 1 };
// @ts-expect-error candidates cannot promote terminal input to server output.
const input: TerminalInput = { type: "output", data: "" } satisfies TerminalOutput;
// @ts-expect-error a single combined dimension is unavailable.
const dimension: Rating["dimension"] = "overall";
void [
  errorCode,
  service,
  empty,
  audioFrame,
  isFinal,
  limitations,
  missingAttempt,
  input,
  dimension,
];
