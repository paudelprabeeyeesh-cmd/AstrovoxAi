export interface IEmbedder {
  name: string;
  /**
   * Embed multiple inputs into vectors. Returns an array of float vectors corresponding to inputs
   */
  embed(inputs: string[], options?: { namespace?: string; model?: string; signal?: AbortSignal }): Promise<number[][]>;

  /**
   * Returns the dimensionality of produced embeddings when known, otherwise undefined
   */
  getDimension(): number | undefined;

  /**
   * Optional warmup/init step
   */
  init?(): Promise<void>;

  shutdown?(): Promise<void>;
}
