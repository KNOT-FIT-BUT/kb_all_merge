#!/bin/sh

# file: start_merge.sh
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# author: René Rešetár (xreset00@stud.fit.vutbr.cz)
# description: merges wikipedia and wikidata2 KB

# constants
project_folder="$(readlink -f $0 | xargs -I{} dirname {})"
wikidata2="$project_folder"/../../kb_resources/kb_all_wikidata
kb_compare=="$project_folder"/../kb_compare.py
wikipedia_KB='http://knot.fit.vutbr.cz/NAKI_CPK/NER_ML_inputs/KB/KB_cs/new/KB.tsv'

prefix_artist='a'
prefix_group='g'
prefix_location='l'
prefix_person='p'

# list dump names
if [ "$1" = "--list" ]; then
	echo "Available dumps:"
	for f in $(ls "$wikidata2"/tsv_extracted_from_wikidata/);
	do
		echo "$f"
	done
	exit 0
fi

# help
if [ "$1" = "--help" ]; then
	echo "Usage:"
	echo "  sh start_merge.sh [ wikidata_dump_name ] [ wikipedia_kb_url ]"
	echo "Example:"
	echo "  sh start_merge.sh wikidata-20210802-all.json http://knot.fit.vutbr.cz/NAKI_CPK/NER_ML_inputs/KB/KB_cs/KB_cs_20210820-1630566298/KB.tsv"
	echo "Description:"
	echo "  Dump name is name of folder in $wikidata2/tsv_extracted_from_wikidata/"
	echo "  When '--list' argument is used list of available dumps is printed."
	echo "  If no arguments are used latest available dump is used."
	exit 0
fi

# if no dump is specified - use lates one (last in list)
if [ -z "$1" ]; then
	dump_name="$(sh "$0" --list | tail -n1)"
else # dump name is passed in
	dump_name="$1"
fi

if [ -n "$2" ]; then
	wikipedia_KB="$2"
fi

[ -d "$wikidata2"/tsv_extracted_from_wikidata/"$dump_name" ] || { echo "Dump $dump_name not available"'!'; exit 1; }

wikidata_person="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-cs-person.tsv
wikidata_arist="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-cs-artist.tsv
wikidata_group="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-cs-group.tsv
wikidata_location="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-cs-location.tsv

# setup
cf="$pwd" # save location
cd "$project_folder"
[ -d output ] || mkdir output
# wikipedia
curl -o KB.tsv "$wikipedia_KB" # get KB
[ -f KB.tsv ] || { echo "Failed to download KB"'!'; exit 1; }

awk -F'\t' '{ if($2=="person") print }' KB.tsv > person/WIKIPEDIA
awk -F'\t' '{ if($2=="artist") print }' KB.tsv > artist/WIKIPEDIA
awk -F'\t' '{ if($2=="person+group") print }' KB.tsv > group/WIKIPEDIA
awk -F'\t' '{ if($2=="geographical") print }' KB.tsv > location/WIKIPEDIA

rm KB.tsv # clean the KB

# wikidata2
cp "$wikidata_person" "$project_folder"/person/WIKIDATA2
cp "$wikidata_arist" "$project_folder"/artist/WIKIDATA2
cp "$wikidata_group" "$project_folder"/group/WIKIDATA2
cp "$wikidata_location" "$project_folder"/location/WIKIDATA2

# merge
for type in artist group location person; do
	cd "$project_folder/$type/"
	echo "Starting to merge $type KB"
	python3 "$kb_compare" \
		--first WIKIDATA2 \
		--second WIKIPEDIA \
		--rel_conf "$type"_rel.conf \
		--output_conf "$type"_output.conf \
		--other_output_conf "$type"_other_output.conf \
		--output "$type"_merged.tsv \
		--treshold 3 \
		--id_prefix "$(eval echo "\$prefix_$type")"
	# cleanup
	rm WIKIDATA2 WIKIPEDIA
	# move result to output folder
	mv -t "$project_folder"/output/ "$type"_merged.tsv
done

# merge files into KB
sh "$project_folder"/mkkb.sh "$dump_name"

cd "$cf" # restore location

