import { STOPWORDS } from "./stopwords.js";
import { fileURLToPath } from "url";

const { readFile } = await import("fs/promises");

let MODEL = null;

async function loadModel() {
  if (MODEL) return MODEL;

  const url = new URL("./model.json", import.meta.url);

  // Detect Node vs Browser
  if (url.protocol === "file:") {
      // Node.js path
      const filePath = fileURLToPath(url);
      try {
        const data = await readFile(filePath, "utf-8");
        MODEL = JSON.parse(data);
      } catch (error) {
        console.error('Error reading model file:', error);
        throw error;
      }
  } else {
      // Browser / Extension path
      console.log('BROWSER environment detected');
      const response = await fetch(url);
      MODEL = await response.json();
  }

  return MODEL;
}

function tokenize(text) {
  // Matches sklearn token_pattern
  const tokens = text.toLowerCase().match(/\b\w\w+\b/g) || [];

  return tokens.filter(t => !MODEL.stopwords.includes(t));
}

function generateNgrams(tokens) {
  const ngrams = [...tokens]; // unigrams

  for (let i = 0; i < tokens.length - 1; i++) {
      ngrams.push(tokens[i] + " " + tokens[i + 1]);
  }

  return ngrams;
}

function computeTF(ngrams, vocabSize) {
  const tf = new Array(vocabSize).fill(0);

  ngrams.forEach(term => {
      const idx = MODEL.vocab[term];
      if (idx !== undefined) {
          tf[idx] += 1;
      }
  });

  return tf;
}

function applyTFIDF(tf) {
  return tf.map((val, i) => val * MODEL.idf[i]);
}

function normalize(vec) {
  let norm = 0;

  for (let v of vec) norm += v * v;

  norm = Math.sqrt(norm);

  if (norm === 0) return vec;

  return vec.map(v => v / norm);
}

function sigmoid(z) {
  return 1 / (1 + Math.exp(-z));
}

function predictProbability(features) {
  let score = MODEL.bias;

  for (let i = 0; i < features.length; i++) {
      score += features[i] * MODEL.weights[i];
  }

  return sigmoid(score);
}

function predict(query) {

  const tokens = tokenize(query);
  const ngrams = generateNgrams(tokens);

  const termCounts = {};

  for (const term of ngrams) {
      const idx = MODEL.vocab[term];
      if (idx !== undefined) {
          termCounts[idx] = (termCounts[idx] || 0) + 1;
      }
  }

  // TF-IDF + norm
  let norm = 0;
  const values = [];

  for (const idx in termCounts) {
      const val = termCounts[idx] * MODEL.idf[idx];
      values.push([Number(idx), val]);
      norm += val * val;
  }

  norm = Math.sqrt(norm) || 1;

  // Logistic regression
  let score = MODEL.bias;

  for (const [idx, val] of values) {
      score += (val / norm) * MODEL.weights[idx];
  }

  const probLLM = 1 / (1 + Math.exp(-score));

  return probLLM;
}

const THRESHOLD = 0.65;

function classify(query) {
  const probLLM = predict(query);

  return {
      route: probLLM > THRESHOLD ? "llm" : "search",
      confidence: Math.max(probLLM, 1 - probLLM),
      probability: probLLM
  };
}

// function classify(query) {

//   const tokens = tokenize(query);

//   const ngrams = generateNgrams(tokens);

//   const tf = computeTF(ngrams, MODEL.idf.length);

//   let tfidf = applyTFIDF(tf);

//   tfidf = normalize(tfidf);

//   const probLLM = predictProbability(tfidf);

//   return {
//       route: probLLM > 0.5 ? "llm" : "search",
//       confidence: Math.max(probLLM, 1 - probLLM)
//   };
// }

// Load model and then test classification
(async () => {
  await loadModel();
  console.log('Model loaded, testing classification...');
  const result = classify("who let the dogs out");
  console.log('Classification result:', result);
})();