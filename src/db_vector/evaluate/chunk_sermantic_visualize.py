from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import numpy as np
import re

from src.db_vector.utils import generate_embeddings


def visualize(distances, y_upper_bound, breakpoint_percentile_threshold):
    plt.plot(distances)

    plt.ylim(0, y_upper_bound)
    plt.xlim(0, len(distances))

    breakpoint_distance_threshold = np.percentile(distances, breakpoint_percentile_threshold)
    plt.axhline(y=breakpoint_distance_threshold, color='r', linestyle='-')

    num_distances_above_threshold = len([x for x in distances if x > breakpoint_distance_threshold])
    plt.text(x=(len(distances) * .01), y=y_upper_bound / 50, s=f"{num_distances_above_threshold + 1} Chunks")

    indices_above_thresh = [i for i, x in enumerate(distances) if x > breakpoint_distance_threshold]

    colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
    for i, breakpoint_index in enumerate(indices_above_thresh):
        start_index = 0 if i == 0 else indices_above_thresh[i - 1]
        end_index = breakpoint_index if i < len(indices_above_thresh) - 1 else len(distances)

        plt.axvspan(start_index, end_index, facecolor=colors[i % len(colors)], alpha=0.25)
        plt.text(x=np.average([start_index, end_index]),
                 y=breakpoint_distance_threshold + (y_upper_bound) / 20,
                 s=f"Chunk #{i}", horizontalalignment='center',
                 rotation='vertical')

    if indices_above_thresh:
        last_breakpoint = indices_above_thresh[-1]
        if last_breakpoint < len(distances):
            plt.axvspan(last_breakpoint, len(distances), facecolor=colors[len(indices_above_thresh) % len(colors)],
                        alpha=0.25)
            plt.text(x=np.average([last_breakpoint, len(distances)]),
                     y=breakpoint_distance_threshold + (y_upper_bound) / 20,
                     s=f"Chunk #{len(indices_above_thresh)}",
                     rotation='vertical')

    plt.title("PG Essay Chunks Based On Embedding Breakpoints")
    plt.xlabel("Index of sentences in essay (Sentence Position)")
    plt.ylabel("Cosine distance between sequential sentences")
    plt.show()
    return indices_above_thresh


def combine_sentences(sentences, buffer_size=1):
    for i in range(len(sentences)):
        combined_sentence = ''

        for j in range(i - buffer_size, i):
            if j >= 0:
                combined_sentence += sentences[j]['sentence'] + ' '

        combined_sentence += sentences[i]['sentence']

        for j in range(i + 1, i + 1 + buffer_size):
            if j < len(sentences):
                combined_sentence += ' ' + sentences[j]['sentence']

        sentences[i]['combined_sentence'] = combined_sentence.strip()

    return sentences


def calculate_cosine_distances(sentences):
    distances = []
    for i in range(len(sentences) - 1):
        embedding_current = sentences[i]['combined_sentence_embedding']
        embedding_next = sentences[i + 1]['combined_sentence_embedding']

        # Calculate cosine similarity
        similarity = cosine_similarity([embedding_current], [embedding_next])[0][0]

        # Convert to cosine distance
        distance = 1 - similarity

        # Append cosine distance to the list
        distances.append(distance)

        # Store distance in the dictionary
        sentences[i]['distance_to_next'] = distance

    return distances, sentences


def chunk_semantic(text):
    # Splitting the essay on '.', '?', and '!'
    single_sentences_list = re.split(r'(?<=[.?!])\s+', text)
    print(f"{len(single_sentences_list)} sentences were found {single_sentences_list}")
    sentences = [{'sentence': x, 'index': i} for i, x in enumerate(single_sentences_list)]
    sentences = combine_sentences(sentences)
    # Calculate embeddings for combined sentences
    for i, sentence in enumerate(sentences):
        combined_sentence_ = sentence['combined_sentence']
        print(combined_sentence_)
        documents = generate_embeddings(combined_sentence_)
        sentences[i]['combined_sentence_embedding'] = documents

    distances, sentences = calculate_cosine_distances(sentences)
    print(distances[:3])

    start_index = 0
    chunks = []
    y_upper_bound = .2
    breakpoint_percentile_threshold = 95
    indices_above_thresh = visualize(distances, y_upper_bound, breakpoint_percentile_threshold)
    for index in indices_above_thresh:
        end_index = index
        group = sentences[start_index:end_index + 1]
        combined_text = ' '.join([d['sentence'] for d in group])
        chunks.append(combined_text)
        start_index = index + 1

    if start_index < len(sentences):
        combined_text = ' '.join([d['sentence'] for d in sentences[start_index:]])
        chunks.append(combined_text)

    for i, chunk in enumerate(chunks[:2]):
        buffer = 200

        print(f"Chunk #{i}")
        print(chunk[:buffer].strip())
        print("...")
        print(chunk[-buffer:].strip())
        print("\n")
    return chunks
