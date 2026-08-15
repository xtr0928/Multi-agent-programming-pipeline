def mean(scores):
    return sum(scores) / len(scores)


def median(scores):
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    mid = n // 2
    if n % 2 == 1:
        return sorted_scores[mid]
    return (sorted_scores[mid - 1] + sorted_scores[mid]) / 2


def pass_rate(scores):
    return len([s for s in scores if s >= 60]) / len(scores)


if __name__ == "__main__":
    sample = [55, 60, 75, 80, 90]
    print("mean:", mean(sample))
    print("median:", median(sample))
    print("pass_rate:", pass_rate(sample))

    sample_even = [50, 60, 70, 80]
    print("median (even):", median(sample_even))
