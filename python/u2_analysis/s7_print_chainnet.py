from collections import defaultdict

from python.common.common import open_pickle, save_text_block, info, open_json

version = open_json('data/chainnet.json')['metadata']['version']

output = r'''\documentclass[11pt]{article}
\usepackage[a4paper, margin=0.8in]{geometry}
\usepackage[T1]{fontenc} 
\usepackage[english]{babel} 
\usepackage[dvipsnames]{xcolor}
\usepackage[normalem]{ulem}
\usepackage{amsmath,amsfonts,amsthm}
\usepackage{latexsym}
\usepackage{tikz}
\usepackage{tikz-dependency}
\usepackage{graphicx}
\usepackage{float}
\usepackage{bm}
\usepackage{adjustbox}
\usepackage{pifont}
\usepackage{sectsty} 
\usepackage{times}
\sectionfont{\normalfont \Large \scshape}
\makeatletter
\renewcommand{\maketitle}{\bgroup\setlength{\parindent}{0pt}
\begin{center}
  {\@title}
\end{center}\egroup
}
\makeatother

\newcommand{\word}[1]{\textit{#1}}
\newcommand{\sense}[2]{\text{\word{#1}}{$_#2$}}
\newcommand{\sensebf}[2]{\textbf{\word{#1}}{$\bm{_#2}$}}
\newcommand{\synonym}[1]{\textit{#1}}

\newcommand{\prototypecolour}{Brown}
\newcommand{\metonymycolour}{Bittersweet}
\newcommand{\metaphorcolour}{Purple}

\newcommand{\prototypelabel}{Prototype}
\newcommand{\metonymylabel}{Metonymy}
\newcommand{\metaphorlabel}{Metaphor}

\renewcommand{\footnotesize}{\fontsize{8pt}{9pt}\selectfont}

\title{
\Large {ChainNet}\\
[10pt] 
}

\pgfdeclarelayer{bg}
\pgfsetlayers{bg,main}
\pgfkeys{%
  /tikz/on layer/.code={
    \pgfonlayer{#1}\begingroup
    \aftergroup\endpgfonlayer
    \aftergroup\endgroup
  }
}
\newcommand{\defaultdepth}{0pt}

\tikzset{definition/.style={align=left, shape=rectangle,draw=black, font={\footnotesize}, fill=black!0!white}}
\tikzset{prototype_definition/.style={anchor=center, align=left, shape=rectangle,draw=\prototypecolour, font={\footnotesize}, label={[text depth=\defaultdepth,anchor=north west]south west:{\footnotesize{\textcolor{\prototypecolour}{\prototypelabel}}}}, fill=black!0!white, line width=1}}
\tikzset{metaphor_definition/.style={anchor=center, align=left, shape=rectangle,draw=\metaphorcolour, font={\footnotesize}, label={[text depth=\defaultdepth, anchor=north west]south west:{\footnotesize{\textcolor{\metaphorcolour}{\metaphorlabel}}}}, fill=black!0!white, line width=.3mm}}
\tikzset{metonymy_definition/.style={anchor=center, align=left, shape=rectangle,draw=\metonymycolour, font={\footnotesize}, label={[text depth=\defaultdepth,anchor=north west]south west:{\footnotesize{\textcolor{\metonymycolour}{\metonymylabel}}}}, fill=black!0!white, line width=.3mm}}

\tikzset{derivation/.style={node distance = 1cm and .5cm}}
\tikzset{metaphor/.style={->, line width=.3mm, \metaphorcolour, rounded corners=2mm, on layer=bg}}
\tikzset{metonymy/.style={->, line width=.3mm, \metonymycolour, on layer=bg}}
\tikzset{start/.style={->, line width=.3mm, \prototypecolour, on layer=bg}}
\tikzset{split/.style={-, dashed, line width=.3mm, Gray, on layer=bg}}

\begin{document}

\onecolumn
\maketitle
'''

output += f'''
\\paragraph{{ChainNet Version {version}}} The following is an automatically-generated PDF containing every ChainNet annotation.
Because it was generated automatically, there are likely to be rendering mistakes.
Each section corresponds to a word.
The graphical representation is similar to the paper, except that labels are shown on senses, and metonymy edges are curved.
These changes make it possible to render words with many senses.
A red star by a section indicates that the annotator did not know that word;
a red star by a sense ID indicates that the annotator did not know that sense.
Features are not shown.
'''

chainnet = open_pickle('bin/analysis/chainnet.pkl')

chapters = defaultdict(str)
for i, wordform in enumerate(sorted(chainnet.keys())):

    word = chainnet[wordform]

    title = wordform.upper()
    if not word.known:
        title += "\\textsuperscript{\\textcolor{Red}{$\\star$}}"

    chapters[wordform[:2]] += f'\n\\section{{{title}}}\n'+word.get_tikz()+'\n'

for chapter_code, chapter_output in chapters.items():

    output += f"\n\\input{{latex/{chapter_code}}}"
    save_text_block(f'bin/analysis/latex/{chapter_code}.tex', chapter_output)

output += '\n\n\\end{document}'
save_text_block('bin/analysis/chainnet.tex', output)

info('Done')
