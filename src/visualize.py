"""Publication plots: fixed units, seed bootstrap intervals, accessible styling."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import numpy as np
import seaborn as sns
try:
    from .process_data import ROOT, process
except ImportError:
    from process_data import ROOT, process

COLORS = ['#0072B2', '#D55E00']
METHODS = ['list','set']
LABELS = ['List (baseline)','Set (proposed)']


def style():
    sns.set_theme(style='whitegrid',context='paper',font_scale=1.15)
    plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,
        'axes.titleweight':'bold','axes.spines.top':False,'axes.spines.right':False,
        'savefig.dpi':300,'figure.dpi':130})


def save(fig,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path.with_suffix('.pdf'),bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None})
    fig.savefig(path.with_suffix('.png'),dpi=300,bbox_inches='tight')
    plt.close(fig)


def make_figures(summary,seeds,out=None):
    style(); out = Path(out or ROOT/'reports/figures')
    fig,axes = plt.subplots(1,3,figsize=(10,3.9),sharey=True,layout='constrained')
    for ax,rate,letter in zip(axes,[0,.5,1],['a','b','c']):
        for method,label,color,marker,line in zip(METHODS,LABELS,COLORS,['o','s'],['--','-']):
            rows=summary.loc[summary.hit_rate.eq(rate)&summary.method.eq(method)].sort_values('size')
            ax.errorbar(rows['size'],rows.mean_lookup_ns_median,
                yerr=np.vstack([rows.mean_lookup_ns_median-rows.mean_lookup_ns_ci_low,
                                rows.mean_lookup_ns_ci_high-rows.mean_lookup_ns_median]),
                color=color,label=label,marker=marker,linestyle=line,capsize=4,linewidth=1.5)
            ax.fill_between(rows['size'].to_numpy(),rows.mean_lookup_ns_ci_low.to_numpy(),
                            rows.mean_lookup_ns_ci_high.to_numpy(),color=color,alpha=.14)
        ax.set(xscale='log',yscale='log',title=f'({letter}) Hit rate {rate:.0%}',xlabel='Container size (keys)')
        ax.set_xticks([100,1000,10000],['100','1,000','10,000'])
        ax.grid(True,which='major',alpha=.35)
    axes[0].set_ylabel('Median batch-average lookup time (ns/query)')
    axes[0].legend(loc='upper left',frameon=True,fontsize=9)
    fig.suptitle('Lookup scaling with 95% bootstrap confidence intervals',fontsize=12)
    save(fig,out/'fig1_latency_vs_load')

    fig,axes=plt.subplots(1,2,figsize=(8,4.2),layout='constrained')
    jitter=np.random.default_rng(42).uniform(-.1,.1,30)
    for ax,method,label,color,marker in zip(axes,METHODS,LABELS,COLORS,['o','s']):
        values=seeds.loc[seeds['size'].eq(10000)&seeds.hit_rate.eq(.5)&seeds.method.eq(method),'mean_lookup_ns'].to_numpy()
        row=summary.loc[summary['size'].eq(10000)&summary.hit_rate.eq(.5)&summary.method.eq(method)].iloc[0]
        ax.boxplot([values],positions=[1],widths=.40,patch_artist=True,showfliers=False,
            boxprops={'facecolor':color,'alpha':.20},medianprops={'color':'black','linewidth':1.8},
            whiskerprops={'color':'#555555'},capprops={'color':'#555555'})
        ax.scatter(1+jitter,values,color=color,marker=marker,s=18,alpha=.60,zorder=3)
        ax.errorbar([1.42],[row.mean_lookup_ns_median],
            yerr=[[row.mean_lookup_ns_median-row.mean_lookup_ns_ci_low],
                  [row.mean_lookup_ns_ci_high-row.mean_lookup_ns_median]],
            fmt='D',color='black',capsize=5,markersize=5,label='Median and 95% CI')
        ax.set(xlim=(.65,1.65),title=label,xlabel='Implementation (category)',
               ylabel='Seed median lookup time (ns/query)')
        ax.set_xticks([1,1.42],[method,'95% CI']);ax.legend(loc='upper right',fontsize=8)
        ax.ticklabel_format(axis='y',style='plain',useOffset=False)
    fig.suptitle('Primary condition: 10,000 keys, 50% hits, 30 seeds\nSeparate linear y-scales show within-method variability',fontsize=11)
    save(fig,out/'fig2_distribution_boxplot')
    return [out/'fig1_latency_vs_load.png',out/'fig2_distribution_boxplot.png']


if __name__ == '__main__':
    _,_,summary,seeds,*_ = process()
    for path in make_figures(summary,seeds): print(path.relative_to(ROOT))
