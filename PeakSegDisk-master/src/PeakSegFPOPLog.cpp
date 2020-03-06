/* -*- compile-command: "R CMD INSTALL .." -*- */

#include <iomanip> //for setprecision.
#include <fstream> //for ifstream etc.
#include <exception>//for std::exception
#include <stdexcept>//for std::invalid_argument
#include <R.h> // Rprintf

#include "funPieceListLog.h"
#include "PeakSegFPOPLog.h"

int PiecewiseFunSize(const PiecewisePoissonLossLog&fun){
  int sizeof_piece = 2*sizeof(double) + sizeof(int);
  return sizeof_piece*fun.piece_list.size() +
    sizeof(int)*2; // n_pieces and chromEnd.
}

void PiecewiseFunCopy(void *dest, const PiecewisePoissonLossLog&fun){
  char *p = (char*)dest;
  int n_pieces = fun.piece_list.size();
  memcpy(p, &n_pieces, sizeof(int));
  p += sizeof(int);
  memcpy(p, &(fun.chromEnd), sizeof(int));
  p += sizeof(int);
  for(PoissonLossPieceListLog::const_iterator it = fun.piece_list.begin();
      it != fun.piece_list.end(); it++){
    memcpy(p, &(it->max_log_mean), sizeof(double));
    p += sizeof(double);
    memcpy(p, &(it->data_i), sizeof(int));
    p += sizeof(int);
    memcpy(p, &(it->prev_log_mean), sizeof(double));
    p += sizeof(double);
  }
}

void PiecewiseFunRestore(PiecewisePoissonLossLog&fun, const void *src){
  int n_pieces;
  char *p = (char*)src;
  PoissonLossPieceLog piece;
  memcpy(&n_pieces, p, sizeof(int));
  p += sizeof(int);
  memcpy(&(fun.chromEnd), p, sizeof(int));
  p += sizeof(int);
  double min_log_mean = -INFINITY;
  for(int piece_i=0; piece_i < n_pieces; piece_i++){
    piece.min_log_mean = min_log_mean;
    memcpy(&(piece.max_log_mean), p, sizeof(double));
    p += sizeof(double);
    memcpy(&(piece.data_i), p, sizeof(int));
    p += sizeof(int);
    memcpy(&(piece.prev_log_mean), p, sizeof(double));
    p += sizeof(double);
    fun.piece_list.push_back(piece);
    min_log_mean = piece.max_log_mean;
  }
}

class UndefinedReadException : public std::exception {
  const char * what() const throw(){
    return "Attempt to read from undefined position";
  }
};

class AlreadyWrittenException : public std::exception {
  const char * what() const throw(){
    return "Attempt to write from already defined position";
  }
};

class WriteFailedException : public std::exception {
  const char * what() const throw(){
    return "Attempt to write to file failed";
  }
};

class DiskVector {
public:
  std::fstream db; //fstream supports both input and output.
  std::streampos beginning;
  int n_entries;
  void init(const char *filename, int N){
    n_entries = N;
    db.open(filename, std::ios::binary|std::ios::in|std::ios::out|std::ios::trunc);
    // reserve the first n_entries for streampos objects that will
    // tell us where to look for the data.
    beginning = db.tellp();
    for(int i=0; i<n_entries;i++){
      write_or_exception((char*)&beginning, sizeof(std::streampos));
    }
  }
  void write_or_exception(char * p, int size){
    db.write(p, size);
    if(db.fail()){
      throw WriteFailedException();
    }
  }
  void seek_element(int element){
    db.seekp(sizeof(std::streampos)*element, std::ios::beg);
  }
  std::streampos get_element_position(int element){
    seek_element(element);
    std::streampos pos;
    db.read((char*)&pos, sizeof(std::streampos));
    return pos;
  }
  PiecewisePoissonLossLog read(int element){
    std::streampos pos = get_element_position(element);
    if(pos == beginning){
      throw UndefinedReadException();
    }
    db.seekp(pos);
    int size;
    db.read((char*)&size, sizeof(int));
    void * buffer = malloc(size);
    db.read((char*)buffer, size);
    PiecewisePoissonLossLog fun;
    PiecewiseFunRestore(fun, buffer);
    free(buffer);
    return fun;
  }
  void write(int element, PiecewisePoissonLossLog fun){
    std::streampos pos = get_element_position(element);
    if(pos != beginning){
      throw AlreadyWrittenException();
    }
    // serialize at end of file.
    db.seekp(0, std::ios::end);
    pos = db.tellp();//save pos for later.
    // first write size of fun.
    int size = PiecewiseFunSize(fun);
    write_or_exception((char*)&size, sizeof(int));
    // then write the data itself.
    void * buffer = malloc(size);
    PiecewiseFunCopy(buffer, fun);
    write_or_exception((char*)buffer, size);
    free(buffer);
    // write position.
    seek_element(element);
    write_or_exception((char*)&pos, sizeof(std::streampos));
  }
};

int PeakSegFPOP_disk
(char *bedGraph_file_name, char* penalty_str, char *db_file_name){
  bool penalty_is_Inf = strcmp(penalty_str, "Inf") == 0;
  double penalty;
  try{
    penalty = std::stod(penalty_str);
  }catch(const std::invalid_argument& e){
    return ERROR_PENALTY_NOT_NUMERIC;
  }
  // Handle penalty error cases before opening files.
  if(penalty_is_Inf){
    //ok, will run special case later, no need to run PDPA.
  }else if(!std::isfinite(penalty)){
    return ERROR_PENALTY_NOT_FINITE;
  }else if(penalty < 0){
    return ERROR_PENALTY_NEGATIVE;
  }
  std::ifstream bedGraph_file(bedGraph_file_name);
  if(!bedGraph_file.is_open()){
    return ERROR_UNABLE_TO_OPEN_BEDGRAPH;
  }
  std::string line;
  int chromStart, chromEnd, coverage, items, line_i=0;
  char chrom[100];
  char extra[100] = "";
  double cum_weight_i = 0.0, cum_weight_prev_i=-1.0, cum_weighted_count=0.0;
  double min_log_mean=INFINITY, max_log_mean=-INFINITY, log_data;
  int data_i = 0;
  double weight;
  int first_chromStart=-1, prev_chromEnd=-1;
  while(std::getline(bedGraph_file, line)){
    line_i++;
    items = sscanf
      (line.c_str(),
       "%s %d %d %d%s\n",
       chrom, &chromStart, &chromEnd, &coverage, extra);
    //Rprintf("%s %d %d %d%s\n", chrom, chromStart, chromEnd, coverage, extra);
    if(items < 4){
      Rprintf("problem: %d items on line %d\n", items, line_i);
      return ERROR_NOT_ENOUGH_COLUMNS;
    }
    if(0 < strlen(extra)){
      return ERROR_NON_INTEGER_DATA;
    }
    weight = chromEnd-chromStart;
    cum_weight_i += weight;
    cum_weighted_count += weight*coverage;
    if(line_i == 1){
      first_chromStart = chromStart;
    }else{
      if(chromStart != prev_chromEnd){
	return ERROR_INCONSISTENT_CHROMSTART_CHROMEND;
      }
    }      
    prev_chromEnd = chromEnd;
    log_data = log( (double)coverage );
    if(log_data < min_log_mean){
      min_log_mean = log_data;
    }
    if(max_log_mean < log_data){
      max_log_mean = log_data;
    }
  }
  int data_count = line_i;
  if(data_count==0){
    return ERROR_NO_DATA;
  }
  double best_cost, best_log_mean, prev_log_mean;
  // open segments and loss files for writing.
  std::string penalty_prefix = bedGraph_file_name;
  penalty_prefix += "_penalty=";
  penalty_prefix += penalty_str;
  std::string segments_file_name = penalty_prefix + "_segments.bed";
  std::string loss_file_name = penalty_prefix + "_loss.tsv";
  std::ofstream segments_file, loss_file; // ofstream supports output only.
  // Opening both files here is fine even if we error exit, because
  // "any open file is automatically closed when the ofstream object
  // is destroyed."
  // http://www.cplusplus.com/reference/fstream/ofstream/close/
  loss_file.open(loss_file_name.c_str());
  segments_file.open(segments_file_name.c_str());
  if(penalty_is_Inf || min_log_mean == max_log_mean){
    // trivial model has one segment, no need to run DP.
    if(cum_weighted_count != 0){
      best_cost = cum_weighted_count *
	(1 - log(cum_weighted_count) + log(cum_weight_i)); 
    } else {
      best_cost = 0;
    }
    segments_file << chrom << "\t" << first_chromStart << "\t" << chromEnd << "\tbackground\t" << cum_weighted_count/cum_weight_i << "\n";
    loss_file << std::setprecision(20) << penalty_str << //penalty constant
      "\t" << 1 << //segments
      "\t" << 0 << //peaks
      "\t" << (int)cum_weight_i << //total bases
      "\t" << data_count << //bedGraph_lines
      "\t" << best_cost/cum_weight_i << //mean penalized cost
      "\t" << best_cost << //total un-penalized cost
      "\t" << 0 << //n_constraints_equal
      "\t" << 0 << //mean intervals
      "\t" << 0 << //max intervals
      "\n";
  }else{// non-trivial model, need to run DP.
    bedGraph_file.clear();
    bedGraph_file.seekg(0, std::ios::beg);
    DiskVector cost_model_mat;
    try{
      cost_model_mat.init(db_file_name, data_count*2);
    }catch(WriteFailedException& e){
      return ERROR_WRITING_COST_FUNCTIONS;
    }
    PiecewisePoissonLossLog up_cost, down_cost, up_cost_prev, down_cost_prev;
    PiecewisePoissonLossLog min_prev_cost;
    int verbose=0;
    cum_weight_i = 0;
    double total_intervals = 0.0, max_intervals = 0.0;
    while(std::getline(bedGraph_file, line)){
      items = sscanf(line.c_str(), "%*s\t%d\t%d\t%d\n", &chromStart, &chromEnd, &coverage);
      weight = chromEnd-chromStart;
      cum_weight_i += weight;
      // if(data_i < 10 || data_i > 1192280){
      //   Rprintf("data_i=%d weight=%f cum=%f coverage=%d\n",
      // 	     data_i, weight, cum_weight_i, coverage);
      // }
      if(data_i==0){
	// initialization Cdown_1(m)=gamma_1(m)/w_1
	down_cost.piece_list.emplace_back
	  (1.0, (double)-coverage, 0.0,
	   min_log_mean, max_log_mean, -1, -5.0);
      }else{
	// if data_i is up, it could have come from down_cost_prev.
	min_prev_cost.set_to_min_less_of(&down_cost_prev, verbose);
	int status = min_prev_cost.check_min_of(&down_cost_prev, &down_cost_prev);
	if(status){
	  Rprintf("BAD MIN LESS CHECK data_i=%d status=%d\n", data_i, status);
	  min_prev_cost.set_to_min_less_of(&down_cost_prev, true);
	  Rprintf("=prev down cost\n");
	  down_cost_prev.print();
	  Rprintf("=min less(prev down cost)\n");
	  min_prev_cost.print();
	  throw status;
	}
	// C^up_t(m) = (gamma_t + w_{1:t-1} * M^up_t(m))/w_{1:t}, where
	// M^up_t(m) = min{
	//   C^up_{t-1}(m),
	//   C^{<=}_down_{t-1}(m) + lambda/w_{1:t-1}
	// in other words, we need to divide the penalty by the previous cumsum,
	// and add that to the min-less-ified function, before applying the min-env.
	min_prev_cost.set_prev_seg_end(data_i-1);
	// cost + lambda * model.complexity =
	// cost + penalty * peaks =>
	// penalty = lambda * model.complexity / peaks.
	// lambda is output by exactModelSelection,
	// penalty is input by PeakSegFPOP.
	min_prev_cost.add(0.0, 0.0, penalty/cum_weight_prev_i);
	if(data_i==1){
	  up_cost = min_prev_cost;
	}else{
	  up_cost.set_to_min_env_of(&min_prev_cost, &up_cost_prev, verbose);
	  status = up_cost.check_min_of(&min_prev_cost, &up_cost_prev);
	  if(status){
	    Rprintf("BAD MIN ENV CHECK data_i=%d status=%d\n", data_i, status);
	    up_cost.set_to_min_env_of(&min_prev_cost, &up_cost_prev, true);
	    Rprintf("=prev down cost\n");
	    down_cost_prev.print();
	    Rprintf("=min less(prev down cost) + %f\n", penalty);
	    min_prev_cost.print();
	    Rprintf("=prev up cost\n");
	    up_cost_prev.print();
	    Rprintf("=new up cost model\n");
	    up_cost.print();
	    throw status;
	  }
	}
	up_cost.multiply(cum_weight_prev_i);
	up_cost.add
	  (weight,
	   -coverage*weight,
	   0.0);
	up_cost.multiply(1/cum_weight_i);
	//Rprintf("computing down cost\n");
	// compute down_cost.
	if(data_i==1){
	  //for second data point, the cost is only a function of the
	  //previous down cost (there is no first up cost).
	  down_cost = down_cost_prev;
	}else{
	  // if data_i is down, it could have come from up_cost_prev.
	  // if(data_i==2329683){
	  //   Rprintf("computing cost data_i=%d\n", data_i);
	  //   verbose=1;
	  // }else{
	  //   verbose=0;
	  // }
	  min_prev_cost.set_to_min_more_of(&up_cost_prev, verbose);
	  status = min_prev_cost.check_min_of(&up_cost_prev, &up_cost_prev);
	  if(status){
	    Rprintf("BAD MIN MORE CHECK data_i=%d status=%d\n", data_i, status);
	    min_prev_cost.set_to_min_more_of(&up_cost_prev, true);
	    Rprintf("=prev up cost\n");
	    up_cost_prev.print();
	    Rprintf("=min more(prev up cost)\n");
	    min_prev_cost.print();
	    throw status;
	  }
	  min_prev_cost.set_prev_seg_end(data_i-1);
	  //NO PENALTY FOR DOWN CHANGE
	  down_cost.set_to_min_env_of(&min_prev_cost, &down_cost_prev, verbose);
	  status = down_cost.check_min_of(&min_prev_cost, &down_cost_prev);
	  if(status){
	    Rprintf("BAD MIN ENV CHECK data_i=%d status=%d\n", data_i, status);
	    down_cost.set_to_min_env_of(&min_prev_cost, &down_cost_prev, true);
	    Rprintf("=prev up cost\n");
	    up_cost_prev.print();
	    Rprintf("=min more(prev up cost)\n");
	    min_prev_cost.print();
	    Rprintf("=prev down cost\n");
	    down_cost_prev.print();
	    Rprintf("=new down cost model\n");
	    down_cost.print();
	    throw status;
	  }
	}//if(data_i==1) else
	down_cost.multiply(cum_weight_prev_i);
	down_cost.add
	  (weight,
	   -coverage*weight,
	   0.0);
	down_cost.multiply(1/cum_weight_i);
      }//if(data_i==0) initialization else update
      cum_weight_prev_i = cum_weight_i;
      total_intervals += up_cost.piece_list.size() + down_cost.piece_list.size();
      if(max_intervals < up_cost.piece_list.size()){
	max_intervals = up_cost.piece_list.size();
      }
      if(max_intervals < down_cost.piece_list.size()){
	max_intervals = down_cost.piece_list.size();
      }
      up_cost_prev = up_cost;
      down_cost_prev = down_cost;
      //Rprintf("data_i=%d data_i+data_count=%d\n", data_i, data_i+data_count);
      up_cost.chromEnd = chromEnd;
      down_cost.chromEnd = chromEnd;
      //try{
      //cost_model_mat[data_i] = up_cost;
      //cost_model_mat[data_i + data_count] = down_cost;
      try{
	// up_cost is undefined for the first data point.
	//Rprintf("data_i=%d up=%d down=%d\n", data_i, up_cost.piece_list.size(), down_cost.piece_list.size());
	cost_model_mat.write(data_i + data_count, down_cost);
	if(0<data_i)cost_model_mat.write(data_i, up_cost);
      }catch(WriteFailedException& e){
	return ERROR_WRITING_COST_FUNCTIONS;
      }
      data_i++;
    }//while(can read line in text file)
    //Rprintf("AFTER\n");
    // Decoding the cost_model_vec, and writing to the output matrices.
    int prev_seg_end;
    int prev_seg_offset = 0;
    // last segment is down (offset N) so the second to last segment is
    // up (offset 0).
    down_cost.Minimize
      (&best_cost, &best_log_mean,
       &prev_seg_end, &prev_log_mean);
    //Rprintf("mean=%f end_i=%d chromEnd=%d\n", exp(best_log_mean), prev_seg_end, down_cost.chromEnd);
    prev_chromEnd = down_cost.chromEnd;
    // mean_vec[0] = exp(best_log_mean);
    // end_vec[0] = prev_seg_end;
    int n_equality_constraints = 0;
    line_i=1;
    while(0 <= prev_seg_end){
      line_i++;
      // up_cost is actually either an up or down cost.
      //up_cost = cost_model_mat[prev_seg_offset + prev_seg_end];
      up_cost = cost_model_mat.read(prev_seg_offset + prev_seg_end);
      //Rprintf("decoding prev_seg_end=%d prev_seg_offset=%d\n", prev_seg_end, prev_seg_offset);
      segments_file << chrom << "\t" << up_cost.chromEnd << "\t" << prev_chromEnd << "\t";
      // change prev_seg_offset for next iteration.
      if(prev_seg_offset==0){
	//up_cost is actually up
	prev_seg_offset = data_count;
	segments_file << "background"; // prev segment is down.
      }else{
	//up_cost is actually down
	prev_seg_offset = 0;
	segments_file << "peak";
      }
      segments_file << "\t" << exp(best_log_mean) << "\n";
      prev_chromEnd = up_cost.chromEnd;
      if(prev_log_mean != INFINITY){
	//equality constraint inactive
	best_log_mean = prev_log_mean;
      }else{
	n_equality_constraints++;
      }
      up_cost.findMean
	(best_log_mean, &prev_seg_end, &prev_log_mean);
      //Rprintf("mean=%f end=%d chromEnd=%d\n", exp(best_log_mean), prev_seg_end, up_cost.chromEnd);
    }//for(data_i
    segments_file << chrom << "\t" << first_chromStart << "\t" << prev_chromEnd << "\tbackground\t" << exp(best_log_mean) << "\n";
    int n_peaks = (line_i-1)/2;
    loss_file << std::setprecision(20) << penalty << //penalty constant
      "\t" << line_i << //segments
      "\t" << n_peaks << //peaks
      "\t" << (int)cum_weight_i << //total bases
      "\t" << data_count << //bedGraph_lines
      "\t" << best_cost << //mean penalized cost
      "\t" << best_cost*cum_weight_i-penalty*n_peaks << //total un-penalized cost
      "\t" << n_equality_constraints <<
      "\t" << total_intervals/(data_count*2) <<
      "\t" << max_intervals <<
      "\n";
  }
  if(loss_file.fail()){
    return ERROR_WRITING_LOSS_OUTPUT;
  }
  if(segments_file.fail()){
    return ERROR_WRITING_SEGMENTS_OUTPUT;
  }
  return 0;
}

