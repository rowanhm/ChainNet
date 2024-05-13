import os
from collections import defaultdict

from python.common.common import open_pickle, get_file_list, open_dict_csv, save_text_block, info

from nltk.corpus import wordnet as wn
def main():

    output = r'''\documentclass[11pt]{article}
    \setlength{\columnsep}{0.35in}
    \usepackage[a4paper, margin=0.8in]{geometry}
    \usepackage{lipsum,mwe,abstract}
    \usepackage[T1]{fontenc} 
    \usepackage[english]{babel} 
    \usepackage{enumitem}

    \usepackage{fancyhdr} % Custom headers and footers
    \pagestyle{fancyplain} % Makes all pages in the document conform to the custom headers and footers
    \fancyhead{} 
    \fancyfoot[C]{\thepage} % Page numbering for right footer
    \usepackage{lipsum}
    \setlength\parindent{4ex} 
    \usepackage[dvipsnames]{xcolor}
    \usepackage[normalem]{ulem}
    \usepackage{multirow}
    \usepackage{amsmath,amsfonts,amsthm} % Math packages
    \usepackage{slashed}
    \usepackage{algorithm}
    \usepackage{enumitem}
    \usepackage{latexsym}

    %\usepackage[symbol]{footmisc}

    %\renewcommand{\thefootnote}{\fnsymbol{footnote}}

    \usepackage{tikz}
    \usepackage{tikz-dependency}

    \usepackage{pifont}% http://ctan.org/pkg/pifont
    \newcommand{\cmark}{{\color{Green} \ding{51}}}%
    \newcommand{\xmark}{{\color{Red} \ding{55}}}%

    \usepackage{wrapfig}
    \usepackage{graphicx}
    \usepackage{float}
    \usepackage[font=small,labelfont=bf]{caption}
    \usepackage{subcaption}
    \usepackage{enumitem}
    \usepackage{cuted}
    \usepackage{comment}
    \usepackage{booktabs}
    \usepackage{sectsty} % Allows customizing section commands
    %\allsectionsfont{\normalfont \normalsize \scshape} % Section names in small caps and normal fonts
    \sectionfont{\normalfont \Large \scshape}
    \subsectionfont{\normalfont \large \rmshape \bfseries}
    \subsubsectionfont{\normalfont \normalsize \rmshape \bfseries}

    \usepackage{makecell}

    \renewenvironment{abstract} % Change how the abstract look to remove margins
     {\small
      \begin{center}
      \bfseries \abstractname\vspace{-.5em}\vspace{0pt}
      \end{center}
      \list{}{%
        \setlength{\leftmargin}{0mm}
        \setlength{\rightmargin}{\leftmargin}%
      }
      \item\relax}
     {\endlist}

    \makeatletter
    \renewcommand{\maketitle}{\bgroup\setlength{\parindent}{0pt} % Change how the title looks like
    \begin{flushleft}
      {\@title}
      \@author \\ 
      \@date
    \end{flushleft}\egroup
    }
    \makeatother

    \usepackage{times}
    \usepackage{latexsym}
    \usepackage{graphicx}

    %\renewcommand{\UrlFont}{\ttfamily\small}

    \usepackage{amsmath}
    \usepackage[colorlinks=true,allcolors=blue]{hyperref}

    \usepackage{cleveref}
    \usepackage{float}
    \usepackage{bm}
    \usepackage{calc}
    \usepackage[font=small]{subfig}
    \crefname{section}{\S}{\S\S}
    \Crefname{section}{\S}{\S\S}
    \crefname{table}{Table}{}
    \crefname{figure}{Figure}{}
    \crefname{algorithm}{Algorithm}{}
    \crefname{equation}{}{}
    \crefname{appendix}{App.}{}
    \crefname{prop}{Proposition}{}
    \crefformat{section}{\S#2#1#3}
    \usepackage{todonotes}
    \usepackage{microtype}
    \usepackage{etoolbox}
    \usepackage{tikz}
    \usepackage{adjustbox}
    \usepackage{tikz-dependency}

    \def\signed #1{{\leavevmode\unskip\nobreak\hfil\penalty50\hskip2em
      \hbox{}\nobreak\hfil(#1)%
      \parfillskip=0pt \finalhyphendemerits=0 \endgraf}}

    \newsavebox\mybox
    \newenvironment{aquote}[1]
      {\savebox\mybox{#1}\begin{quote}}
      {\signed{\usebox\mybox}\end{quote}}

    \usepackage{natbib}
    \setcitestyle{authoryear, open={(},close={)}}

    \newcommand{\citeposs}[1]{\citeauthor{#1}'s (\citeyear{#1})}
    \newcommand{\tabspace}{\addlinespace[0.7em]}

    \newcommand{\word}[1]{\textit{#1}}
    \newcommand{\sense}[2]{\text{\word{#1}}{$_#2$}}
    \newcommand{\sensebf}[2]{\textbf{\word{#1}}{$\bm{_#2}$}}
    \newcommand{\synonym}[1]{\textit{#1}}

    \newcommand{\corecolour}{Brown}
    \newcommand{\metonymycolour}{Bittersweet}
    \newcommand{\metaphorcolour}{Purple}
    \newcommand{\conduitcolour}{Gray}

    \newcommand{\corelabel}{Core}
    \newcommand{\metonymylabel}{metonymy}
    \newcommand{\metaphorlabel}{metaphor}
    \newcommand{\conduitlabel}{Conduit}

    \newcommand{\newfeature}[1]{#1}
    \newcommand{\keptfeature}[1]{\textcolor{Green}{\newfeature{#1}}}
    \usepackage[normalem]{ulem}
    \newcommand{\lostfeature}[1]{\textcolor{Red}{\sout{\newfeature{#1}}}}
    \newcommand{\modifiedfeature}[1]{\textcolor{Orange}{\newfeature{#1}}}

    \title{
    \Large {Annotation}\\
    [10pt] 
    }
    \author{~~\vspace{-1em}}
    \date{}

    \pgfdeclarelayer{bg}    % declare background layer
    \pgfsetlayers{bg,main}  % set the order of the layers (main is the standard layer)

    \pgfkeys{%
      /tikz/on layer/.code={
        \pgfonlayer{#1}\begingroup
        \aftergroup\endpgfonlayer
        \aftergroup\endgroup
      }
    }

    \newcommand{\defaultdepth}{0pt}
    \tikzset{definition/.style={align=left, shape=rectangle,draw=black, font={\footnotesize}, fill=black!0!white}}
    \tikzset{core_definition/.style={anchor=center, align=left, shape=rectangle,draw=\corecolour, font={\footnotesize}, label={[text depth=\defaultdepth,anchor=south west]north west:{\footnotesize{\textcolor{\corecolour}{\corelabel}}}}, fill=black!0!white, line width=1}}
    \tikzset{metaphor_definition/.style={anchor=center, align=left, shape=rectangle,draw=\metaphorcolour, font={\footnotesize}, label={[text depth=\defaultdepth, anchor=south west]north west:{\footnotesize{\textcolor{\metaphorcolour}{\metaphorlabel}}}}, fill=black!0!white, line width=.3mm}}
    \tikzset{metonymy_definition/.style={anchor=center, align=left, shape=rectangle,draw=\metonymycolour, font={\footnotesize}, label={[text depth=\defaultdepth,anchor=south west]north west:{\footnotesize{\textcolor{\metonymycolour}{\metonymylabel}}}}, fill=black!0!white, line width=.3mm}}
    \tikzset{metaphorconduit_definition/.style={anchor=center, align=left, shape=rectangle,draw=\metaphorcolour, font={\footnotesize}, label={[text depth=\defaultdepth, anchor=south west]north west:{\footnotesize{\textcolor{\metaphorcolour}{\metaphorlabel}\textcolor{\conduitcolour}{{ }+{ }\conduitlabel}}}}, fill=black!0!white, line width=.3mm}}
    \tikzset{metonymyconduit_definition/.style={anchor=center, align=left, shape=rectangle,draw=\metonymycolour, font={\footnotesize}, label={[text depth=\defaultdepth,anchor=south west]north west:{\footnotesize{\textcolor{\metonymycolour}{\metonymylabel}\textcolor{\conduitcolour}{{ }+{ }\conduitlabel}}}}, fill=black!0!white, line width=.3mm}}

    \tikzset{derivation/.style={node distance = 1cm and .5cm}}

    \tikzset{metaphor/.style={->, line width=.3mm, \metaphorcolour, rounded corners=2mm, on layer=bg}}
    \tikzset{association/.style={->, line width=.3mm, \metonymycolour, on layer=bg}}
    \tikzset{start/.style={->, line width=.3mm, \corecolour, on layer=bg}}
    \tikzset{split/.style={--, dashed, line width=.3mm, Gray, on layer=bg}}


    \begin{document}

    \onecolumn
    \maketitle'''

    chainnet = open_pickle('bin/analysis/chainnet.pkl')

    for wordform, word in chainnet.items():

        output += f'\\section{{{wordform.upper()}}}'
        output += '\n'+word.get_tikz()

    output += '\n\\end{document}'
    save_text_block('bin/analysis/chainnet.tex', output)

    info('Done')

if __name__ == "__main__":
    main()
