gnuplot -p -e 'set term dumb 120,30;set key outside; plot "log_gpio22.txt" pt"O";'
gnuplot -p -e 'set term dumb 120,30;set key outside; plot for [col=1:2] "log_gpio22.txt" using 0:col with lines pt".";'
gnuplot -p -e 'set term dumb 120,30;set key outside; plot for [col=1:2:1] "log_gpio22.txt" using col with dots pt".";'
gnuplot -p -e 'set term dumb 120,30;set key outside;set title "Foobar is kuul"; plot [-5:5] sin(x);'
gnuplot -p -e 'set term dumb 120,30;set key outside;set title "Foobar is kuul";set ylabel "Range";  plot [-5:5] sin(x) with impulse;'
gnuplot -p -e 'set term dumb 120,30;set key outside;set title "Foobar is kuul";set ylabel "Y axis Range";set xlabel "X axis Range";set grid;  plot [-5:5] sin(x) with impulse;'

