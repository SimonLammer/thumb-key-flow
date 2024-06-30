#!/usr/bin/python3

import argparse
import csv
from tqdm import tqdm
print = tqdm.write
from math import atan2, pi, sqrt


ARGS = None
CSV_HEADERS = ["precessor", "symbol", "successor", "count"]
CSV_DELIMITER = ","
TRIPLETS: dict[tuple[str, str, str], int] = dict()


def analyze(text: str) -> None:
  precessor = ''
  for start in range(0, len(text)):
    if text[start] != '\n':
      break
  symbol = text[start]
  for successor in tqdm(text[start+1:]):
    if symbol != '':
      key = (precessor, symbol, successor)
      count = TRIPLETS.get(key, 0)
      if successor == '\n':
        successor = ''
        key = (precessor, symbol, successor)
        count = TRIPLETS.get(key, 0)
      TRIPLETS[key] = count + 1
    precessor = symbol
    symbol = successor

def compute_frequency():
  occurrences: dict[str, int] = dict()
  total_occurrences = 0
  letter_occurrences: dict[str, int] = dict()
  total_letter_occurrences = 0
  for (_, symbol, _), count in TRIPLETS.items():
    occurrences[symbol] = occurrences.get(symbol, 0) + count
    total_occurrences += count
    if symbol.isalpha():
      symbol = symbol.lower()
      letter_occurrences[symbol] = letter_occurrences.get(symbol, 0) + count
      total_letter_occurrences += count
  with open(ARGS.frequency[0], 'w+') as f:
    writer = csv.writer(f, delimiter=CSV_DELIMITER)
    writer.writerow(["symbol", "absolute occurrences", "frequency", "letter frequency"])
    for symbol, occurrence in sorted(occurrences.items(), key=lambda x: -x[1]):
      letter_frequency = letter_occurrences.get(symbol.lower())
      if letter_frequency is not None and letter_frequency > 0:
        letter_frequency /= total_letter_occurrences

      writer.writerow([symbol, occurrence, occurrence / total_occurrences, letter_frequency])

def thumb_key_loss(layout_file: str) -> float:
  # report tiplets' influence on loss
  symbols: dict[tuple[float, float], str] = dict()
  positions: dict[str, tuple[float, float]] = dict()
  with open(layout_file, 'r') as f:
    reader = csv.reader(f, delimiter=CSV_DELIMITER)
    for symbol, primary, secondary in reader:
      k = (float(primary), float(secondary))
      symbols[k] = symbol
      positions[symbol] = k

  def coord(pos: int): # x, y
    pos -= 1
    return (pos % 3 - 1, 1 - pos // 3)

  def delta(a: tuple[float, float], b: tuple[float, float]):
    return (b[0] - a[0], b[1] - a[1])

  def add(a: tuple[float, float], b: tuple[float, float]):
    return (a[0] + b[0], a[1] + b[1])

  def dist(a: tuple[float, float], b: tuple[float, float]):
    d = delta(a, b)
    return sqrt(abs(d[0]) ** 2 + abs(d[1]) ** 2)

  def dest(c: tuple[tuple[float, float], tuple[float, float]]):
    return add(c[0], c[1])

  def cos_similarity(v_a: tuple[float, float], v_b: tuple[float, float]):
    sim = 1
    if (0,0) in (v_a, v_b):
      # return 0
      pass
    else:
      sim =  sum([a * b for a, b in zip(v_a, v_b)]) / (dist((0,0), v_a) * (dist((0,0), v_b)))
    print(f"{v_a=} {v_b=} {sim=}")
    return sim

  def angle_loss(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]):
    vecs = [delta(a, b), delta(b, c)]
    # if not all([any(x) for x in vecs]):
    #   return 0
    sim = cos_similarity(*vecs)
    return 1 - sim

  triplet_impact: dict[tuple[str, str, str], float] = dict()
  loss_per_symbol: dict[str, float] = dict()
  total_loss = 0
  for triplet_key, occurrence in tqdm(sorted(TRIPLETS.items(), key=lambda x: -x[1])):
    precessor, symbol, successor = triplet_key
    loss = 0
    syms = [precessor, symbol, successor]
    pos = [positions.get(x) for x in syms]
    if None in pos:
      continue # TODO: revise
    coords = [[coord(p) for p in po] for po in pos]
    dests = [dest(c) for c in coords]

    # loss ... increase of typing cost in comparison to same text without the current symbol

    """
    mps:
      r.m -> h
      h.p -> s
      
    v1: 1 - c_s(m>h -> h, h -> p>r)
    """

    if pos[1][1] != 5: # symbol needs swiping
      loss += 1
    dl1 = 1.5 * dist(dests[0], coords[1][0]) # "unnecessary" movement to get to symbol's main key
    dl2 = dist(coords[1][0], dests[1]) # necessary movement to type the symbol
    # dl2 = dist(dests[1], coords[2][0])
    # al1 = angle_loss(coords[0][0], dests[0], coords[1][0])
    # al2 = angle_loss(coords[1][0], dests[1], coords[2][0])
    # al1 = 1 - cos_similarity(delta(dests[0], coords[1][0]), delta(coords[1][0], dests[1]))
    al1 = 1 - cos_similarity(delta(dests[0], coords[1][0]), delta(coords[1][0], dests[1]))
    al2 = 0
    print(f"{triplet_key=} {pos=} {coords=} {dests=} \t{loss=} \t{dl1=} \t{dl2=} \t{al1=} \t{al2=}")
    # print(f"{triplet_key=} \t{dl1=} \t{dl2=} \t{al1=} \t{al2=}")
    loss += 0.75 * (dl1 + dl2) + 1.5 * (al1 + al2)

    # loss *= occurrence
    total_loss += loss
    triplet_impact[triplet_key] = loss
    loss_per_symbol[symbol] = loss_per_symbol.get(symbol, 0) + loss

    if symbol == 'e':
      break # TODO: remove
  
  for k, loss in sorted(triplet_impact.items(), key=lambda x: -x[1]):#[:30]:
    print(f"triplet {k} is responsible for a loss of {loss} {loss/total_loss}")

  # loss per symbol
  for symbol, loss in sorted(loss_per_symbol.items(), key=lambda x: -x[1]):
    print(f"symbol {symbol} is responsible for a loss of {loss} {loss/total_loss}")

  return total_loss

def load_args():
  global ARGS
  parser = argparse.ArgumentParser(
      prog="thumb-key-flow",
  )
  parser.add_argument("triplets_file")
  parser.add_argument("-a", "--analyze",
      nargs='+',
      help="Compute triplets from these files")
  parser.add_argument("-f", "--frequency",
      nargs=1,
      help="Compute symbol frequency and store it in this file")
  parser.add_argument("-t", "--thumb-key-loss",
      nargs='+',
      help="Compute thumb-key loss of these layouts")
  ARGS = parser.parse_args()

def load_triplets():
  with open(ARGS.triplets_file, 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=CSV_DELIMITER)
    try:
      header = next(reader)
    except StopIteration:
      pass
    for precessor, symbol, successor, count in reader:
      count = int(count)
      TRIPLETS[(precessor, symbol, successor)] = count

def save_triplets():
  with open(ARGS.triplets_file, 'w') as csvfile:
    writer = csv.writer(csvfile, delimiter=CSV_DELIMITER)
    writer.writerow(CSV_HEADERS)
    sorted_triplets = sorted(TRIPLETS.items(), key=lambda x: -x[1])
    for (precessor, symbol, successor), count in sorted_triplets:
      writer.writerow([precessor, symbol, successor, count]);

def main():
  load_args()
  print(f"loading triplets from {ARGS.triplets_file}")
  load_triplets()
  if ARGS.analyze:
    for file in tqdm(ARGS.analyze):
      print(f"analyzing {file}")
      with open(file, 'r') as f:
        analyze(f.read())
  if ARGS.frequency:
    print(f"Computing frequencies")
    compute_frequency()
  if ARGS.thumb_key_loss:
    for file in tqdm(ARGS.thumb_key_loss):
      print(f"computing thumb key loss for {file}")
      x = thumb_key_loss(file)
      print(f"{x}")
  if ARGS.analyze:
    print(f"saving triplets to {ARGS.triplets_file}")
    save_triplets()

if __name__ == '__main__':
  main()

