import matplotlib.pyplot as plt
import pandas as pd

def plot_csv(csv_path, out_png):
    df = pd.read_csv(csv_path)
    fig = plt.figure(figsize=(10,4.2))
    ax = fig.add_subplot(111)
    ax.plot(df["smooth"], label="smooth")
    ax.plot(df["raw"], alpha=0.4, label="raw")
    if "alert" in df:
        alerts = df.index[df["alert"]==1]
        ax.scatter(alerts, df["smooth"].iloc[alerts], marker="o", s=22)
    ax.set_title("Methane Stream (raw vs smooth)")
    ax.set_xlabel("sample")
    ax.set_ylabel("adc/units")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)
